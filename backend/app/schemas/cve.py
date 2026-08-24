from datetime import datetime
from pydantic import BaseModel, ConfigDict


class CveResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    cve_id: str
    title: str | None
    description: str | None
    cvss_score: float | None
    severity: str
    affected_products: list[str]
    references: list[str]
    published_at: datetime | None
    last_modified_at: datetime | None
    source: str
    synced_at: datetime


class CveListResponse(BaseModel):
    data: list[CveResponse]
    total: int
    page: int
    page_size: int


class CveSyncResponse(BaseModel):
    status: str
    fetched: int
    updated: int
    message: str
