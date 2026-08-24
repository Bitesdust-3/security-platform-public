"""SQLAlchemy database foundation.

The production database URL must be supplied through DATABASE_URL. A local
SQLite fallback keeps health checks and metadata tests independent of MySQL.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.base import Base

# SQLite is intentionally retained for local tests and development. Production
# deployments must be explicit: silently falling back to a container-local file
# would make MySQL configuration failures look like data loss.
if not settings.database_url and settings.environment.lower() == "production":
    raise RuntimeError("DATABASE_URL must be configured when ENVIRONMENT=production")

DATABASE_URL = settings.database_url or "sqlite:///./security_platform.db"
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
