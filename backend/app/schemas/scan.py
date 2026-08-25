from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ScanCreate(BaseModel):
    task_name: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=64)
    scan_type: str = Field(default="port_scan", pattern="^port_scan$")


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_name: str
    target: str
    scan_type: str
    status: str
    result_summary: str | None
    created_by: int | None
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ScanResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    scan_task_id: int
    asset_id: int | None
    result_type: str
    ip_address: str | None
    port: int | None
    protocol: str | None
    service_name: str | None
    product_name: str | None
    service_version: str | None
    raw_summary: str | None
    normalized_data: str | None
    created_at: datetime
