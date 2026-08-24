from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models import Asset, AssetService, AssetVulnerability, Vulnerability
from app.schemas.vulnerability import VulnerabilityAssetCreate, VulnerabilityAssetResponse, VulnerabilityAssetUpdate, VulnerabilityCreate, VulnerabilityListResponse, VulnerabilityResponse, VulnerabilityStatistics, VulnerabilityUpdate
from app.models import ScanTask
from app.services.risk import calculate_risk_score
from app.services.audit import record_audit

router = APIRouter(prefix="/vulnerabilities")


def _audit(db: DbSession, user_id: int, action: str, vulnerability_id: int, detail: str) -> None:
    record_audit(db, user_id=user_id, action=action, resource="vulnerability", resource_id=vulnerability_id, description=detail)


@router.get("", response_model=VulnerabilityListResponse, summary="漏洞列表")
def list_vulnerabilities(db: DbSession, _: CurrentUser, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), severity: str | None = Query(None, pattern="^(info|low|medium|high|critical)$"), status_filter: str | None = Query(None, alias="status", pattern="^(open|processing|fixed|ignored)$"), cve_id: str | None = Query(None, max_length=32), asset_id: int | None = Query(None, ge=1)) -> VulnerabilityListResponse:
    filters = []
    if severity:
        filters.append(Vulnerability.severity == severity)
    if cve_id:
        filters.append(Vulnerability.cve_id == cve_id)
    if status_filter:
        filters.append(Vulnerability.status == status_filter)
    if asset_id:
        filters.append(Vulnerability.asset_id == asset_id)
    total = db.scalar(select(func.count()).select_from(Vulnerability).where(*filters)) or 0
    items = db.scalars(select(Vulnerability).where(*filters).order_by(Vulnerability.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return VulnerabilityListResponse(data=items, page=page, page_size=page_size, total=total)


@router.post("", response_model=VulnerabilityResponse, status_code=status.HTTP_201_CREATED, summary="创建漏洞")
def create_vulnerability(payload: VulnerabilityCreate, user: AdminUser, db: DbSession) -> Vulnerability:
    if payload.asset_id is not None and db.get(Asset, payload.asset_id) is None:
        raise HTTPException(status_code=404, detail="资产不存在")
    if payload.scan_task_id is not None and db.get(ScanTask, payload.scan_task_id) is None:
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    vulnerability = Vulnerability(**payload.model_dump())
    db.add(vulnerability)
    db.flush()
    _audit(db, user.id, "create", vulnerability.id, "创建漏洞")
    db.commit()
    db.refresh(vulnerability)
    return vulnerability


@router.get("/statistics", response_model=VulnerabilityStatistics, summary="漏洞统计")
def vulnerability_statistics(_: CurrentUser, db: DbSession) -> VulnerabilityStatistics:
    rows = db.execute(select(Vulnerability.severity, func.count()).group_by(Vulnerability.severity)).all()
    counts = {severity: 0 for severity in ("critical", "high", "medium", "low")}
    total = 0
    for severity, count in rows:
        total += int(count)
        if severity in counts:
            counts[severity] = int(count)
    return VulnerabilityStatistics(total=total, **counts)


@router.get("/{vulnerability_id}", response_model=VulnerabilityResponse, summary="漏洞详情")
def get_vulnerability(vulnerability_id: int, _: CurrentUser, db: DbSession) -> Vulnerability:
    vulnerability = db.get(Vulnerability, vulnerability_id)
    if vulnerability is None:
        raise HTTPException(status_code=404, detail="漏洞不存在")
    return vulnerability


@router.patch("/{vulnerability_id}", response_model=VulnerabilityResponse, summary="更新漏洞")
@router.put("/{vulnerability_id}", response_model=VulnerabilityResponse, summary="更新漏洞")
def update_vulnerability(vulnerability_id: int, payload: VulnerabilityUpdate, user: AdminUser, db: DbSession) -> Vulnerability:
    vulnerability = db.get(Vulnerability, vulnerability_id)
    if vulnerability is None:
        raise HTTPException(status_code=404, detail="漏洞不存在")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(vulnerability, key, value)
    _audit(db, user.id, "update", vulnerability.id, "更新漏洞")
    db.commit()
    db.refresh(vulnerability)
    return vulnerability


@router.delete("/{vulnerability_id}", status_code=status.HTTP_204_NO_CONTENT, summary="忽略漏洞")
def delete_vulnerability(vulnerability_id: int, user: AdminUser, db: DbSession) -> None:
    vulnerability = db.get(Vulnerability, vulnerability_id)
    if vulnerability is None:
        raise HTTPException(status_code=404, detail="漏洞不存在")
    vulnerability.status = "ignored"
    _audit(db, user.id, "ignore", vulnerability.id, "忽略漏洞")
    db.commit()


@router.post("/{vulnerability_id}/assets/{asset_id}", response_model=VulnerabilityAssetResponse, status_code=status.HTTP_201_CREATED, summary="关联漏洞资产")
def attach_asset(vulnerability_id: int, asset_id: int, payload: VulnerabilityAssetCreate, user: CurrentUser, db: DbSession) -> AssetVulnerability:
    vulnerability = db.get(Vulnerability, vulnerability_id)
    asset = db.get(Asset, asset_id)
    if vulnerability is None or asset is None:
        raise HTTPException(status_code=404, detail="漏洞或资产不存在")
    existing = db.scalar(select(AssetVulnerability).where(AssetVulnerability.vulnerability_id == vulnerability_id, AssetVulnerability.asset_id == asset_id))
    if existing is not None:
        raise HTTPException(status_code=409, detail="漏洞已关联该资产")
    has_service = db.scalar(select(AssetService.id).where(AssetService.asset_id == asset_id).limit(1)) is not None
    now = datetime.now(timezone.utc)
    link = AssetVulnerability(asset_id=asset_id, vulnerability_id=vulnerability_id, status=payload.status, risk_score=calculate_risk_score(vulnerability.severity, asset.importance, has_service, vulnerability.cvss_score), first_seen_at=now, last_seen_at=now)
    db.add(link)
    db.flush()
    _audit(db, user.id, "attach_asset", vulnerability_id, f"关联资产 {asset_id}")
    db.commit()
    db.refresh(link)
    return link


@router.patch("/{vulnerability_id}/assets/{asset_id}", response_model=VulnerabilityAssetResponse, summary="更新资产漏洞状态")
def update_asset_vulnerability(vulnerability_id: int, asset_id: int, payload: VulnerabilityAssetUpdate, user: CurrentUser, db: DbSession) -> AssetVulnerability:
    link = db.scalar(select(AssetVulnerability).where(AssetVulnerability.vulnerability_id == vulnerability_id, AssetVulnerability.asset_id == asset_id))
    if link is None:
        raise HTTPException(status_code=404, detail="漏洞资产关联不存在")
    if payload.status is not None:
        link.status = payload.status
        if payload.status == "fixed":
            link.fixed_at = datetime.now(timezone.utc)
    if payload.verification_note is not None:
        link.verification_note = payload.verification_note
    _audit(db, user.id, "update_asset_status", vulnerability_id, f"更新资产 {asset_id} 漏洞状态")
    db.commit()
    db.refresh(link)
    return link
