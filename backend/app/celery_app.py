from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "security_platform",
    broker=settings.redis_url,
    backend=settings.celery_result_backend,
    include=["app.tasks.scan_tasks", "app.tasks.cve_tasks"],
)
celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "dispatch-due-scan-schedules": {
            "task": "app.tasks.scan_tasks.dispatch_due_schedules",
            "schedule": 30.0,
        },
        "sync-cve-intelligence": {
            "task": "app.tasks.cve_tasks.sync_cve_task",
            "schedule": 21600.0,
        },
    },
)
