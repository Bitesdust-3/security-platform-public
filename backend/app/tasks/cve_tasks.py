from app.celery_app import celery_app
from app.database import SessionLocal
from app.services.cve_sync import sync_nvd


@celery_app.task(bind=True, autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def sync_cve_task(self):
    db = SessionLocal()
    try:
        return sync_nvd(db)
    finally:
        db.close()
