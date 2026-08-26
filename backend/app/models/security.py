from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.mysql import LONGTEXT
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for all application defaults."""
    return datetime.now(timezone.utc)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    is_active: Mapped[bool] = mapped_column(default=True)
    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users")
    scan_tasks: Mapped[list["ScanTask"]] = relationship(back_populates="creator")


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    users: Mapped[list[User]] = relationship(secondary="user_roles", back_populates="roles")


class UserRole(Base):
    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_name: Mapped[str] = mapped_column(String(128), index=True)
    asset_type: Mapped[str] = mapped_column(String(32), index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), index=True)
    hostname: Mapped[Optional[str]] = mapped_column(String(255))
    os_info: Mapped[Optional[str]] = mapped_column(String(255))
    environment: Mapped[Optional[str]] = mapped_column(String(32))
    importance: Mapped[int] = mapped_column(Integer, default=3)
    owner: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    services: Mapped[list["AssetService"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class AssetService(Base):
    __tablename__ = "asset_services"
    __table_args__ = (UniqueConstraint("asset_id", "port", "protocol"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    port: Mapped[int] = mapped_column(Integer)
    protocol: Mapped[str] = mapped_column(String(16))
    service_name: Mapped[Optional[str]] = mapped_column(String(128))
    service_version: Mapped[Optional[str]] = mapped_column(String(128))
    discovered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    asset: Mapped[Asset] = relationship(back_populates="services")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(32))
    resource_type: Mapped[str] = mapped_column(String(64))
    resource_id: Mapped[Optional[int]] = mapped_column(Integer)
    resource: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    detail: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)


class ScanTask(TimestampMixin, Base):
    __tablename__ = "scan_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_name: Mapped[str] = mapped_column(String(128))
    target: Mapped[str] = mapped_column(String(255))
    scan_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    result_summary: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    schedule_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scan_schedules.id", ondelete="SET NULL"), index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    creator: Mapped[Optional[User]] = relationship(back_populates="scan_tasks", foreign_keys=[created_by])


class ScanSchedule(TimestampMixin, Base):
    __tablename__ = "scan_schedules"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_name: Mapped[str] = mapped_column(String(128))
    target: Mapped[str] = mapped_column(String(255))
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), index=True)
    scan_type: Mapped[str] = mapped_column(String(32), default="port_scan")
    schedule_type: Mapped[str] = mapped_column(String(16), default="once")
    execute_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    cron_expression: Mapped[Optional[str]] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    creator: Mapped[Optional[User]] = relationship(foreign_keys=[created_by])
    asset: Mapped[Optional[Asset]] = relationship(foreign_keys=[asset_id])


class ScanResult(Base):
    __tablename__ = "scan_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    scan_task_id: Mapped[int] = mapped_column(ForeignKey("scan_tasks.id", ondelete="CASCADE"), index=True)
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), index=True)
    result_type: Mapped[str] = mapped_column(String(32))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), index=True)
    port: Mapped[Optional[int]] = mapped_column(Integer, index=True)
    protocol: Mapped[Optional[str]] = mapped_column(String(16))
    port_state: Mapped[Optional[str]] = mapped_column(String(16))
    service_name: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    service_version: Mapped[Optional[str]] = mapped_column(String(128))
    raw_summary: Mapped[Optional[str]] = mapped_column(Text)
    normalized_data: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class Vulnerability(TimestampMixin, Base):
    __tablename__ = "vulnerabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    cve_id: Mapped[Optional[str]] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16), index=True)
    cvss_score: Mapped[Optional[float]] = mapped_column()
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    asset_id: Mapped[Optional[int]] = mapped_column(ForeignKey("assets.id", ondelete="SET NULL"), index=True)
    scan_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey("scan_tasks.id", ondelete="SET NULL"), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    remediation: Mapped[Optional[str]] = mapped_column(Text)
    fixed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    remark: Mapped[Optional[str]] = mapped_column(Text)
    source: Mapped[Optional[str]] = mapped_column(String(64))
    asset: Mapped[Optional[Asset]] = relationship(foreign_keys=[asset_id])
    scan_task: Mapped[Optional[ScanTask]] = relationship(foreign_keys=[scan_task_id])


class CveIntelligence(TimestampMixin, Base):
    __tablename__ = "cve_intelligence"

    id: Mapped[int] = mapped_column(primary_key=True)
    cve_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    cvss_score: Mapped[Optional[float]] = mapped_column()
    severity: Mapped[str] = mapped_column(String(16), index=True, default="info")
    affected_products: Mapped[Optional[str]] = mapped_column(Text)
    references: Mapped[Optional[str]] = mapped_column(Text)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    last_modified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, index=True)
    source: Mapped[str] = mapped_column(String(32), default="NVD")
    raw_data: Mapped[Optional[str]] = mapped_column(Text().with_variant(LONGTEXT(), "mysql"))
    synced_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)


class SecurityReport(TimestampMixin, Base):
    __tablename__ = "security_reports"
    id: Mapped[int] = mapped_column(primary_key=True)
    report_name: Mapped[str] = mapped_column(String(160))
    period_start: Mapped[datetime] = mapped_column(DateTime)
    period_end: Mapped[datetime] = mapped_column(DateTime)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, index=True)
    asset_count: Mapped[int] = mapped_column(Integer, default=0)
    online_asset_count: Mapped[int] = mapped_column(Integer, default=0)
    high_risk_asset_count: Mapped[int] = mapped_column(Integer, default=0)
    vulnerability_count: Mapped[int] = mapped_column(Integer, default=0)
    cve_count: Mapped[int] = mapped_column(Integer, default=0)
    high_risk_vulnerability_count: Mapped[int] = mapped_column(Integer, default=0)
    risk_distribution: Mapped[str] = mapped_column(Text, default="{}")
    scan_statistics: Mapped[str] = mapped_column(Text, default="{}")
    vulnerability_trend: Mapped[str] = mapped_column(Text, default="[]")
    top_risk_assets: Mapped[str] = mapped_column(Text, default="[]")
    top_vulnerabilities: Mapped[str] = mapped_column(Text, default="[]")
    recommendations: Mapped[str] = mapped_column(Text, default="[]")
    report_html: Mapped[Optional[str]] = mapped_column(Text().with_variant(LONGTEXT(), "mysql"))
    status: Mapped[str] = mapped_column(String(16), default="generated", index=True)
    archived_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    archived_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)
    created_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), index=True)


class AssetVulnerability(Base):
    __tablename__ = "asset_vulnerabilities"
    __table_args__ = (UniqueConstraint("asset_id", "vulnerability_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    vulnerability_id: Mapped[int] = mapped_column(ForeignKey("vulnerabilities.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="open", index=True)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    first_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    fixed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    verification_note: Mapped[Optional[str]] = mapped_column(Text)
