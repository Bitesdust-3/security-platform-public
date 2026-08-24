from sqlalchemy.orm import Session

from app.models import AuditLog


def record_audit(db: Session, *, user_id: int | None, action: str, resource: str, description: str, resource_id: int | None = None, ip_address: str | None = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, resource=resource, resource_type=resource, resource_id=resource_id, description=description, detail=description, ip_address=ip_address))
