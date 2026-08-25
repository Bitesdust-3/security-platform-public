import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


backend_path = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(backend_path))
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-32-bytes-long-key")

# Shared in-memory database for processor tests.  Keeping this fixture here
# avoids importing another test module just to obtain its session factory.
from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402,F401  # register all model tables on Base.metadata

_testing_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(_testing_engine)
SessionTesting = sessionmaker(bind=_testing_engine, autoflush=False, autocommit=False)
