from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    action: str
    resource: str | None
    ip_address: str | None
    description: str | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    data: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
