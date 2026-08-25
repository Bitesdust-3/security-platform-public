import subprocess
from datetime import datetime, timezone

from sqlalchemy import select
from croniter import croniter

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import ScanSchedule, ScanTask
from app.services.scanner import nmap_available, run_nmap
from app.services.scan_result_processor import process_scan_results


def _execute_scan(db, scan_task: ScanTask) -> None:
    if not nmap_available():
        raise RuntimeError("系统未安装 Nmap")
    scan_task.status = "running"
    scan_task.started_at = datetime.now(timezone.utc)
    db.commit()
    discovered = run_nmap(scan_task.target)
    now = datetime.now(timezone.utc)
    summary = process_scan_results(db, scan_task, discovered)
    scan_task.status = "completed"
    scan_task.result_summary = (
        f"发现 {summary['discovered_services']} 条开放服务，"
        f"保存 {summary['saved_results']} 条结果，"
        f"匹配 {summary['matched_cves']} 条CVE，"
        f"生成 {summary['created_vulnerabilities']} 条漏洞"
        + (f"，处理警告 {summary['processing_warnings']} 条" if summary["processing_warnings"] else "")
    )
    scan_task.finished_at = now
    db.commit()


@celery_app.task(bind=True, autoretry_for=(OSError, subprocess.TimeoutExpired), retry_backoff=True, max_retries=2)
def run_scan_task(self, scan_task_id: int, schedule_id: int | None = None):
    db = SessionLocal()
    try:
        scan_task = db.get(ScanTask, scan_task_id)
        if scan_task is None:
            return
        try:
            _execute_scan(db, scan_task)
        except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError, RuntimeError) as exc:
            scan_task.status = "failed"
            scan_task.error_message = str(exc)[:1000]
            scan_task.finished_at = datetime.now(timezone.utc)
            db.commit()
            if schedule_id:
                schedule = db.get(ScanSchedule, schedule_id)
                if schedule:
                    schedule.status = "failed"
                    schedule.error_message = str(exc)[:1000]
                    db.commit()
            return
        if schedule_id:
            schedule = db.get(ScanSchedule, schedule_id)
            if schedule:
                schedule.status = "completed"
                schedule.last_run_at = datetime.now(timezone.utc)
                schedule.error_message = None
                if schedule.schedule_type == "once":
                    schedule.next_run_at = None
                else:
                    schedule.status = "pending"
                    expression = schedule.cron_expression or ("0 2 * * *" if schedule.schedule_type == "daily" else "0 2 * * 1")
                    schedule.next_run_at = croniter(expression, datetime.now(timezone.utc)).get_next(datetime)
                db.commit()
    finally:
        db.close()


@celery_app.task
def dispatch_due_schedules():
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        schedules = db.scalars(select(ScanSchedule).where(ScanSchedule.status == "pending", ScanSchedule.next_run_at.is_not(None), ScanSchedule.next_run_at <= now)).all()
        for schedule in schedules:
            task = ScanTask(task_name=schedule.task_name, target=schedule.target, scan_type=schedule.scan_type, created_by=schedule.created_by, schedule_id=schedule.id)
            db.add(task)
            db.flush()
            schedule.status = "running"
            if schedule.schedule_type == "once":
                schedule.next_run_at = None
            db.commit()
            run_scan_task.delay(task.id, schedule.id)
    finally:
        db.close()
