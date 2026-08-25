"""统一处理 Nmap 结果、资产服务和候选 CVE。

该服务不负责执行扫描，只负责扫描完成后的数据落库，确保 Celery
和同步备用路径使用完全相同的处理规则。
"""

import json
import re
from datetime import datetime, timezone

from sqlalchemy import or_, select

from app.models import Asset, AssetService, CveIntelligence, ScanResult, ScanTask, Vulnerability
from app.core.logger import logger
from app.services.scanner import DiscoveredService


def _tokens(value: str | None) -> set[str]:
    if not value:
        return set()
    value = value.lower().strip()
    aliases = {
        "apache httpd": "apache",
        "apache http server": "apache",
        "httpd": "apache",
        "openssh": "open_ssh",
        "microsoft iis": "iis",
    }
    value = aliases.get(value, value)
    parts = {value, value.replace(" ", "_"), value.replace("_", " ")}
    parts.update(re.findall(r"[a-z0-9][a-z0-9.+-]{2,}", value))
    return {part for part in parts if len(part) >= 3}


def _candidate_cves(db, item: DiscoveredService) -> list[tuple[CveIntelligence, str]]:
    """Return candidates and a conservative confidence level.

    Product matching is case-insensitive and supports common Nmap/NVD aliases.
    A version, when available, is required to upgrade confidence to ``high``;
    the record remains a possible match when only the product is known.
    """
    products = _tokens(item.service_name)
    if not products:
        return []
    product_filters = [CveIntelligence.affected_products.ilike(f"%{token}%") for token in products]
    rows = db.scalars(select(CveIntelligence).where(or_(*product_filters)).limit(50)).all()
    version = (item.service_version or "").lower().strip()
    result: list[tuple[CveIntelligence, str]] = []
    for row in rows:
        affected = (row.affected_products or "").lower()
        if version and version in affected:
            result.append((row, "high"))
        else:
            result.append((row, "medium"))
    return result


def process_scan_results(db, scan_task: ScanTask, discovered: list[DiscoveredService]) -> dict[str, int]:
    """Persist discovered services and create de-duplicated possible vulnerabilities."""
    now = datetime.now(timezone.utc)
    saved_results = 0
    matched_cves = 0
    created_vulnerabilities = 0
    possible_matches = 0
    processing_warnings = 0

    logger.info("scan post-process started scan_id=%s discovered=%s", scan_task.id, len(discovered))

    for item in discovered:
        asset = db.scalar(select(Asset).where(Asset.ip_address == item.ip_address))
        if asset is None:
            asset = Asset(asset_name=item.hostname or item.ip_address, asset_type="server", ip_address=item.ip_address, hostname=item.hostname, status="active")
            db.add(asset)
            db.flush()

        service = db.scalar(select(AssetService).where(
            AssetService.asset_id == asset.id,
            AssetService.port == item.port,
            AssetService.protocol == item.protocol,
        ))
        if service is None:
            db.add(AssetService(asset_id=asset.id, port=item.port, protocol=item.protocol,
                                service_name=item.service_name, service_version=item.service_version,
                                discovered_at=now))
        else:
            service.service_name = item.service_name or service.service_name
            service.service_version = item.service_version or service.service_version
            service.discovered_at = now

        db.add(ScanResult(
            scan_task_id=scan_task.id,
            asset_id=asset.id,
            result_type="service",
            ip_address=item.ip_address,
            port=item.port,
            protocol=item.protocol,
            service_name=item.service_name,
            product_name=item.service_name,
            service_version=item.service_version,
            raw_summary=json.dumps({"ip": item.ip_address, "port": item.port, "protocol": item.protocol,
                                    "service": item.service_name, "version": item.service_version}, ensure_ascii=False),
            normalized_data=f"{item.ip_address}:{item.port}/{item.protocol}"
                            f" {item.service_name or 'unknown'} {item.service_version or ''}".strip(),
        ))
        saved_results += 1
        logger.debug("scan result saved scan_id=%s asset_id=%s service=%s version=%s", scan_task.id, asset.id, item.service_name, item.service_version)

        try:
            candidates = _candidate_cves(db, item)
        except Exception:
            # Matching is supplementary to discovery. A CVE query failure must
            # not discard the already persisted service result.
            processing_warnings += 1
            logger.exception("cve matching failed scan_id=%s asset_id=%s service=%s", scan_task.id, asset.id, item.service_name)
            candidates = []

        for cve, confidence in candidates:
            matched_cves += 1
            if confidence != "high":
                possible_matches += 1
            exists = db.scalar(select(Vulnerability).where(
                Vulnerability.cve_id == cve.cve_id,
                Vulnerability.asset_id == asset.id,
            ))
            if exists is not None:
                continue
            try:
                # Flush inside a savepoint so a duplicate/race or a malformed
                # record does not roll back unrelated scan results.
                with db.begin_nested():
                    db.add(Vulnerability(
                        title=cve.title or cve.cve_id,
                        cve_id=cve.cve_id,
                        description=cve.description,
                        severity=cve.severity,
                        cvss_score=cve.cvss_score,
                        status="open",
                        asset_id=asset.id,
                        scan_task_id=scan_task.id,
                        source=f"nvd-possible:{confidence}",
                        remediation="请核实厂商、产品和版本范围后升级到安全版本",
                    ))
                    db.flush()
                created_vulnerabilities += 1
                logger.info("candidate vulnerability created scan_id=%s asset_id=%s cve=%s confidence=%s", scan_task.id, asset.id, cve.cve_id, confidence)
            except Exception:
                processing_warnings += 1
                logger.exception("vulnerability write failed scan_id=%s asset_id=%s cve=%s", scan_task.id, asset.id, cve.cve_id)

    logger.info(
        "scan post-process completed scan_id=%s saved_results=%s matched_cves=%s possible_matches=%s created_vulnerabilities=%s",
        scan_task.id, saved_results, matched_cves, possible_matches, created_vulnerabilities,
    )

    return {
        "discovered_services": len(discovered),
        "saved_results": saved_results,
        "matched_cves": matched_cves,
        "possible_matches": possible_matches,
        "created_vulnerabilities": created_vulnerabilities,
        "processing_warnings": processing_warnings,
    }
