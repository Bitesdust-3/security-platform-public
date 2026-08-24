import json
from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models import CveIntelligence
from app.schemas.cve import CveListResponse, CveResponse, CveSyncResponse
from app.services.cve_sync import decode_json_field
from app.tasks.cve_tasks import sync_cve_task

router = APIRouter(prefix="/cve")


def _response(row: CveIntelligence) -> CveResponse:
    data = {key: getattr(row, key) for key in ("id", "cve_id", "title", "description", "cvss_score", "severity", "published_at", "last_modified_at", "source", "synced_at")}
    data["affected_products"] = decode_json_field(row.affected_products)
    data["references"] = decode_json_field(row.references)
    return CveResponse(**data)


@router.get("", response_model=CveListResponse)
def list_cves(_: CurrentUser, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), keyword: str | None = Query(None, max_length=100), severity: str | None = Query(None, pattern="^(info|low|medium|high|critical)$")):
    filters = [CveIntelligence.severity == severity] if severity else []
    if keyword:
        filters.append(or_(CveIntelligence.cve_id.like(f"%{keyword}%"), CveIntelligence.title.like(f"%{keyword}%"), CveIntelligence.description.like(f"%{keyword}%")))
    total = db.scalar(select(func.count()).select_from(CveIntelligence).where(*filters)) or 0
    rows = db.scalars(select(CveIntelligence).where(*filters).order_by(CveIntelligence.last_modified_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return CveListResponse(data=[_response(row) for row in rows], total=total, page=page, page_size=page_size)


@router.get("/{cve_id}", response_model=CveResponse)
def get_cve(cve_id: str, _: CurrentUser, db: DbSession):
    row = db.scalar(select(CveIntelligence).where(CveIntelligence.cve_id == cve_id))
    if row is None: raise HTTPException(status_code=404, detail="CVE 情报不存在")
    return _response(row)


@router.post("/sync", response_model=CveSyncResponse, status_code=status.HTTP_202_ACCEPTED)
def trigger_sync(_: AdminUser):
    sync_cve_task.delay()
    return CveSyncResponse(status="queued", fetched=0, updated=0, message="CVE 增量同步已提交后台队列")
