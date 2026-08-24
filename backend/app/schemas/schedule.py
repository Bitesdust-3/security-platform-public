from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScheduleCreate(BaseModel):
    task_name: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=255)
    asset_id: int | None = None
    scan_type: str = Field(default="port_scan", pattern="^port_scan$")
    schedule_type: str = Field(default="once", pattern="^(once|daily|weekly|cron)$")
    execute_at: datetime | None = None
    cron_expression: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.schedule_type == "once" and self.execute_at is None:
            raise ValueError("一次性任务必须提供 execute_at")
        if self.schedule_type == "cron" and not self.cron_expression:
            raise ValueError("周期任务必须提供 cron_expression")
        return self


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    task_name: str
    target: str
    asset_id: int | None
    scan_type: str
    schedule_type: str
    execute_at: datetime | None
    cron_expression: str | None
    status: str
    created_by: int | None
    last_run_at: datetime | None
    next_run_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime


class ScheduleUpdate(BaseModel):
    task_name: str | None = Field(default=None, min_length=1, max_length=128)
    target: str | None = Field(default=None, max_length=255)
    schedule_type: str | None = Field(default=None, pattern="^(once|daily|weekly|cron)$")
    execute_at: datetime | None = None
    cron_expression: str | None = Field(default=None, max_length=128)
    status: str | None = Field(default=None, pattern="^(pending|disabled)$")
