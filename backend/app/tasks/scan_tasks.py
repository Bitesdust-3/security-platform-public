import subprocess
from datetime import datetime, timezone

from sqlalchemy import select
from croniter import croniter

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models import Asset, AssetService, CveIntelligence, ScanResult, ScanSchedule, ScanTask, Vulnerability
from app.services.scanner import nmap_available, run_nmap


def _execute_scan(db, scan_task: ScanTask) -> None:
    if not nmap_available():
        raise RuntimeError("系统未安装 Nmap")
    scan_task.status = "running"
    scan_task.started_at = datetime.now(timezone.utc)
    db.commit()
    discovered = run_nmap(scan_task.target)
    now = datetime.now(timezone.utc)
    for item in discovered:
        asset = db.scalar(select(Asset).where(Asset.ip_address == item.ip_address))
        if asset is None:
            asset = Asset(asset_name=item.hostname or item.ip_address, asset_type="server", ip_address=item.ip_address, hostname=item.hostname, status="active")
            db.add(asset)
            db.flush()
        service = db.scalar(select(AssetService).where(AssetService.asset_id == asset.id, AssetService.port == item.port, AssetService.protocol == item.protocol))
        if service is None:
            db.add(AssetService(asset_id=asset.id, port=item.port, protocol=item.protocol, service_name=item.service_name, service_version=item.service_version, discovered_at=now))
        db.add(ScanResult(scan_task_id=scan_task.id, asset_id=asset.id, result_type="service", normalized_data=f"{item.ip_address}:{item.port}/{item.protocol}"))
        # Conservative high-confidence candidate matching: require both product and version in NVD raw data.
        if item.service_name and item.service_version:
            candidates = db.scalars(select(CveIntelligence).where(CveIntelligence.raw_data.like(f"%{item.service_name}%"), CveIntelligence.raw_data.like(f"%{item.service_version}%")).limit(10)).all()
            for cve in candidates:
                exists = db.scalar(select(Vulnerability).where(Vulnerability.cve_id == cve.cve_id, Vulnerability.asset_id == asset.id))
                if exists is None:
                    db.add(Vulnerability(title=cve.title or cve.cve_id, cve_id=cve.cve_id, description=cve.description, severity=cve.severity, cvss_score=cve.cvss_score, status="open", asset_id=asset.id, scan_task_id=scan_task.id, source="nvd-possible", remediation="请核实版本范围并升级到厂商安全版本"))
    scan_task.status = "completed"
    scan_task.result_summary = f"发现 {len(discovered)} 条开放服务"
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
