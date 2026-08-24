from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import AdminUser, DbSession
from app.models import AuditLog
from app.schemas.audit import AuditLogListResponse

router = APIRouter(prefix="/audit")


@router.get("/logs", response_model=AuditLogListResponse, summary="审计日志")
def list_audit_logs(_: AdminUser, db: DbSession, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), action: str | None = Query(None, max_length=64), resource: str | None = Query(None, max_length=128), user_id: int | None = Query(None, ge=1)) -> AuditLogListResponse:
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if resource:
        filters.append(AuditLog.resource == resource)
    if user_id:
        filters.append(AuditLog.user_id == user_id)
    total = db.scalar(select(func.count()).select_from(AuditLog).where(*filters)) or 0
    rows = db.scalars(select(AuditLog).where(*filters).order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return AuditLogListResponse(data=rows, total=total, page=page, page_size=page_size)
