from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from croniter import croniter

from app.api.deps import CurrentUser, DbSession
from app.models import ScanSchedule
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.services.audit import record_audit
from app.services.scanner import ScanTargetError, validate_target_scope
from app.tasks.scan_tasks import run_scan_task
from app.models import ScanTask

router = APIRouter(prefix="/scan-schedules")


def _admin(user):
    return any(role.name == "admin" for role in user.roles)


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_schedule(payload: ScheduleCreate, user: CurrentUser, db: DbSession):
    try:
        target = validate_target_scope(payload.target)
    except ScanTargetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    when = payload.execute_at
    if when and when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    if payload.schedule_type == "cron":
        when = when or croniter(payload.cron_expression, datetime.now(timezone.utc)).get_next(datetime)
    elif payload.schedule_type == "daily":
        when = when or croniter("0 2 * * *", datetime.now(timezone.utc)).get_next(datetime)
    elif payload.schedule_type == "weekly":
        when = when or croniter("0 2 * * 1", datetime.now(timezone.utc)).get_next(datetime)
    schedule = ScanSchedule(**payload.model_dump(exclude={"target", "execute_at"}), target=target, execute_at=when, next_run_at=when, created_by=user.id)
    db.add(schedule)
    db.flush()
    record_audit(db, user_id=user.id, action="create", resource="scan_schedule", resource_id=schedule.id, description="创建定时扫描任务")
    db.commit(); db.refresh(schedule)
    return schedule


@router.get("", response_model=list[ScheduleResponse])
def list_schedules(user: CurrentUser, db: DbSession, limit: int = Query(50, ge=1, le=100)):
    query = select(ScanSchedule).order_by(ScanSchedule.id.desc()).limit(limit)
    if not _admin(user): query = query.where(ScanSchedule.created_by == user.id)
    return list(db.scalars(query).all())


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
def update_schedule(schedule_id: int, payload: ScheduleUpdate, user: CurrentUser, db: DbSession):
    schedule = db.get(ScanSchedule, schedule_id)
    if schedule is None or (schedule.created_by != user.id and not _admin(user)):
        raise HTTPException(status_code=404, detail="定时任务不存在")
    values = payload.model_dump(exclude_unset=True)
    if "target" in values:
        try: values["target"] = validate_target_scope(values["target"])
        except ScanTargetError as exc: raise HTTPException(status_code=400, detail=str(exc)) from exc
    for key, value in values.items(): setattr(schedule, key, value)
    if schedule.status == "pending" and schedule.schedule_type == "daily": schedule.next_run_at = croniter("0 2 * * *", datetime.now(timezone.utc)).get_next(datetime)
    if schedule.status == "pending" and schedule.schedule_type == "weekly": schedule.next_run_at = croniter("0 2 * * 1", datetime.now(timezone.utc)).get_next(datetime)
    if schedule.status == "pending" and schedule.schedule_type == "cron": schedule.next_run_at = croniter(schedule.cron_expression, datetime.now(timezone.utc)).get_next(datetime)
    db.commit(); db.refresh(schedule); return schedule


@router.get("/{schedule_id}/history", response_model=list)
def schedule_history(schedule_id: int, user: CurrentUser, db: DbSession):
    schedule = db.get(ScanSchedule, schedule_id)
    if schedule is None or (schedule.created_by != user.id and not _admin(user)):
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return list(db.scalars(select(ScanTask).where(ScanTask.schedule_id == schedule_id).order_by(ScanTask.id.desc()).limit(50)).all())


@router.post("/{schedule_id}/run", response_model=ScheduleResponse)
def run_schedule(schedule_id: int, user: CurrentUser, db: DbSession):
    schedule = db.get(ScanSchedule, schedule_id)
    if schedule is None or (schedule.created_by != user.id and not _admin(user)):
        raise HTTPException(status_code=404, detail="定时任务不存在")
    if schedule.status == "running": raise HTTPException(status_code=409, detail="任务正在执行")
    task = ScanTask(task_name=schedule.task_name, target=schedule.target, scan_type=schedule.scan_type, created_by=user.id, schedule_id=schedule.id)
    db.add(task); db.flush(); schedule.status = "running"; schedule.last_run_at = datetime.now(timezone.utc); db.commit()
    run_scan_task.delay(task.id, schedule.id)
    db.refresh(schedule)
    return schedule


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(schedule_id: int, user: CurrentUser, db: DbSession):
    schedule = db.get(ScanSchedule, schedule_id)
    if schedule is None or (schedule.created_by != user.id and not _admin(user)):
        raise HTTPException(status_code=404, detail="定时任务不存在")
    db.delete(schedule); db.commit()
