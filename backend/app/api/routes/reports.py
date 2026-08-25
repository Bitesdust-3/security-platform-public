from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy import select
from app.api.deps import AdminUser, CurrentUser, DbSession
from app.models import SecurityReport
from app.schemas.report import ReportCreate, ReportResponse
from app.services.report import as_dict, build_report, render_html
router=APIRouter(prefix="/reports")

def _is_admin(user) -> bool:
    return any(role.name == "admin" for role in user.roles)

def _get_allowed(report_id: int, user, db):
    row = db.get(SecurityReport, report_id)
    if row is None or (row.created_by != user.id and not _is_admin(user)):
        raise HTTPException(404, "报告不存在")
    return row

@router.post("",response_model=ReportResponse,status_code=201)
def create_report(payload:ReportCreate,user:AdminUser,db:DbSession):
    row=build_report(db,payload,user.id); db.add(row); db.flush(); row.report_html = render_html(row); db.commit(); db.refresh(row); return as_dict(row)
@router.get("",response_model=list[ReportResponse])
def list_reports(user:CurrentUser,db:DbSession,limit:int=Query(50,ge=1,le=100)):
    q=select(SecurityReport).order_by(SecurityReport.id.desc()).limit(limit)
    if not _is_admin(user): q=q.where(SecurityReport.created_by==user.id)
    return [as_dict(x) for x in db.scalars(q).all()]
@router.get("/{report_id}",response_model=ReportResponse)
def get_report(report_id:int,user:CurrentUser,db:DbSession):
    row=_get_allowed(report_id,user,db)
    return as_dict(row)

@router.post("/{report_id}/archive", response_model=ReportResponse)
def archive_report(report_id: int, user: AdminUser, db: DbSession):
    row = _get_allowed(report_id, user, db)
    row.status = "archived"
    row.archived_at = datetime.now(timezone.utc)
    row.archived_by = user.id
    db.commit(); db.refresh(row)
    return as_dict(row)
@router.get("/{report_id}/html",response_class=HTMLResponse)
def html_report(report_id:int,user:CurrentUser,db:DbSession):
    row=_get_allowed(report_id,user,db)
    return HTMLResponse(render_html(row))
@router.get("/{report_id}/pdf")
def pdf_report(report_id:int,user:CurrentUser,db:DbSession):
    row=_get_allowed(report_id,user,db)
    try:
        from weasyprint import HTML
        content=HTML(string=render_html(row)).write_pdf()
        return Response(content,media_type="application/pdf",headers={"Content-Disposition":f'attachment; filename="security-report-{row.id}.pdf"'})
    except Exception as exc: raise HTTPException(503,f"PDF 引擎不可用：{exc}") from exc
