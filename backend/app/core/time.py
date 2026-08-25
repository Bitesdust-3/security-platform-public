"""Time helpers for user-facing China Standard Time presentation."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def to_utc_naive(value: datetime) -> datetime:
    """Normalize an API timestamp for UTC DATETIME persistence."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=SHANGHAI_TZ)
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def utc_now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def as_shanghai(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(SHANGHAI_TZ)


def format_shanghai(value: datetime | None) -> str:
    local = as_shanghai(value)
    return local.strftime("%Y-%m-%d %H:%M:%S CST") if local else "-"
