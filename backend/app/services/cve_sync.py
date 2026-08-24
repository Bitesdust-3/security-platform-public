import json
from datetime import datetime, timedelta, timezone

import requests
from sqlalchemy import select

from app.core.config import settings
from app.models import CveIntelligence

NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


def _parse_time(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _severity(score: float | None, label: str | None) -> str:
    normalized = (label or "").lower()
    if normalized in {"critical", "high", "medium", "low"}:
        return normalized
    if score is None:
        return "info"
    return "critical" if score >= 9 else "high" if score >= 7 else "medium" if score >= 4 else "low"


def _normalize(item: dict) -> dict:
    cve = item.get("cve", {})
    descriptions = cve.get("descriptions", [])
    description = next((x.get("value") for x in descriptions if x.get("lang") == "en"), None) or (descriptions[0].get("value") if descriptions else None)
    metrics = cve.get("metrics", {})
    metric = next(iter(metrics.get("cvssMetricV40", [])), None) or next(iter(metrics.get("cvssMetricV31", [])), None) or next(iter(metrics.get("cvssMetricV30", [])), None) or next(iter(metrics.get("cvssMetricV2", [])), None)
    cvss = metric.get("cvssData", {}) if metric else {}
    products: list[str] = []
    for config in cve.get("configurations", []):
        for node in config.get("nodes", []):
            for match in node.get("cpeMatch", []):
                criteria = match.get("criteria")
                if criteria and criteria not in products:
                    products.append(criteria)
    links = [ref.get("url") for ref in cve.get("references", []) if ref.get("url")]
    return {"cve_id": cve.get("id"), "title": (description or cve.get("id"))[:255], "description": description, "cvss_score": cvss.get("baseScore"), "severity": _severity(cvss.get("baseScore"), cvss.get("baseSeverity")), "affected_products": json.dumps(products[:100]), "references": json.dumps(links[:100]), "published_at": _parse_time(cve.get("published")), "last_modified_at": _parse_time(cve.get("lastModified")), "source": "NVD", "raw_data": json.dumps(item, ensure_ascii=False)}


def sync_nvd(db, since: datetime | None = None, until: datetime | None = None) -> tuple[int, int]:
    now = datetime.now(timezone.utc)
    since = since or now - timedelta(days=settings.nvd_sync_days)
    until = until or now
    params = {"lastModStartDate": since.isoformat().replace("+00:00", "Z"), "lastModEndDate": until.isoformat().replace("+00:00", "Z"), "resultsPerPage": 100}
    headers = {"apiKey": settings.nvd_api_key} if settings.nvd_api_key else {}
    response = requests.get(NVD_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    fetched = updated = 0
    for item in response.json().get("vulnerabilities", []):
        data = _normalize(item)
        if not data["cve_id"]: continue
        fetched += 1
        record = db.scalar(select(CveIntelligence).where(CveIntelligence.cve_id == data["cve_id"]))
        if record is None:
            db.add(CveIntelligence(**data, synced_at=now))
        else:
            for key, value in data.items(): setattr(record, key, value)
            record.synced_at = now; updated += 1
    db.commit()
    return fetched, updated


def decode_json_field(value: str | None) -> list[str]:
    try:
        result = json.loads(value or "[]")
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []
