from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models import ScanResult, ScanTask
from app.schemas.scan import ScanCreate, ScanResponse, ScanResultResponse
from app.services.scanner import ScanTargetError, nmap_available, run_nmap, validate_target_scope
from app.services.audit import record_audit
from app.tasks.scan_tasks import run_scan_task
from app.services.scan_result_processor import process_scan_results

router = APIRouter(prefix="/scans")


@router.post("", response_model=ScanResponse, status_code=status.HTTP_201_CREATED, summary="创建扫描任务")
def create_scan(payload: ScanCreate, user: CurrentUser, db: DbSession) -> ScanTask:
    try:
        target = validate_target_scope(payload.target)
    except ScanTargetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    task = ScanTask(task_name=payload.task_name, scan_type=payload.scan_type, target=target, created_by=user.id)
    db.add(task)
    db.flush()
    record_audit(db, user_id=user.id, action="create", resource="scan", resource_id=task.id, description="创建扫描任务")
    db.commit()
    db.refresh(task)
    return task


@router.get("", response_model=list[ScanResponse], summary="扫描任务列表")
def list_scans(user: CurrentUser, db: DbSession, limit: int = Query(20, ge=1, le=100)) -> list[ScanTask]:
    query = select(ScanTask).order_by(ScanTask.id.desc()).limit(limit)
    if not any(role.name == "admin" for role in user.roles):
        query = query.where(ScanTask.created_by == user.id)
    return list(db.scalars(query).all())


@router.get("/{scan_id}", response_model=ScanResponse, summary="扫描任务详情")
def get_scan(scan_id: int, user: CurrentUser, db: DbSession) -> ScanTask:
    task = db.get(ScanTask, scan_id)
    if task is None or (task.created_by != user.id and not any(role.name == "admin" for role in user.roles)):
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    return task


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT, summary="归档扫描任务")
def delete_scan(scan_id: int, user: CurrentUser, db: DbSession) -> None:
    task = db.get(ScanTask, scan_id)
    is_admin = any(role.name == "admin" for role in user.roles)
    if task is None or (task.created_by != user.id and not is_admin):
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    if task.status == "running":
        raise HTTPException(status_code=409, detail="扫描正在执行，不能删除")
    record_audit(db, user_id=user.id, action="archive", resource="scan", resource_id=task.id, description="归档扫描任务")
    task.status = "archived"
    db.commit()


@router.post("/{scan_id}/start", response_model=ScanResponse, summary="启动扫描任务")
def start_scan(scan_id: int, user: CurrentUser, db: DbSession) -> ScanTask:
    task = db.get(ScanTask, scan_id)
    if task is None or (task.created_by != user.id and not any(role.name == "admin" for role in user.roles)):
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    if task.status != "pending":
        raise HTTPException(status_code=409, detail="任务不是待执行状态")
    task.status = "pending"
    db.commit()
    try:
        run_scan_task.delay(task.id)
    except Exception:
        # Local development/tests may not have Redis; retain the original synchronous fallback.
        if not nmap_available():
            task.status = "failed"
            task.error_message = "系统未安装 Nmap"
        else:
            try:
                task.status = "running"
                task.started_at = datetime.now(timezone.utc)
                discovered = run_nmap(task.target)
                summary = process_scan_results(db, task, discovered)
                task.status = "completed"
                task.result_summary = (
                    f"发现 {summary['discovered_services']} 条开放服务，"
                    f"保存 {summary['saved_results']} 条结果，"
                    f"匹配 {summary['matched_cves']} 条CVE，"
                    f"生成 {summary['created_vulnerabilities']} 条漏洞"
                    + (f"，处理警告 {summary['processing_warnings']} 条" if summary["processing_warnings"] else "")
                )
            except Exception as exc:
                task.status = "failed"; task.error_message = str(exc)[:1000]
        task.finished_at = datetime.now(timezone.utc)
        db.commit()
    db.refresh(task)
    return task


@router.get("/{scan_id}/results", response_model=list[ScanResultResponse], summary="扫描结果")
def list_scan_results(scan_id: int, user: CurrentUser, db: DbSession) -> list[ScanResult]:
    task = db.get(ScanTask, scan_id)
    if task is None or (task.created_by != user.id and not any(role.name == "admin" for role in user.roles)):
        raise HTTPException(status_code=404, detail="扫描任务不存在")
    return list(db.scalars(select(ScanResult).where(ScanResult.scan_task_id == scan_id).order_by(ScanResult.id)).all())
