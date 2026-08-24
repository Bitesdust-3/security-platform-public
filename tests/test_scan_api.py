from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.routes import scans as scans_route
from app.core.security import hash_password
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import Asset, Role, User
from app.services.scanner import DiscoveredService

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)
db = SessionTesting()
role = Role(name="admin", description="管理员")
db.add(role)
db.add(User(username="scan-admin", email="scan-admin@example.com", hashed_password=hash_password("scan-password-123"), roles=[role]))
db.commit()
db.close()


def override_get_db() -> Generator[Session, None, None]:
    session = SessionTesting()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_scan_task_and_asset_sync(monkeypatch):
    app.dependency_overrides[get_db] = override_get_db
    # Unit tests must not depend on a live Redis broker. Force the route's
    # documented local fallback so the test remains deterministic and fast.
    monkeypatch.setattr(scans_route.run_scan_task, "delay", lambda *_args, **_kwargs: (_ for _ in ()).throw(ConnectionError("broker disabled in unit test")))
    login = client.post("/api/v1/auth/login", json={"username": "scan-admin", "password": "scan-password-123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post("/api/v1/scans", headers=headers, json={"task_name": "lab discovery", "target": "192.0.2.10", "scan_type": "port_scan"})
    assert created.status_code == 201
    scan_id = created.json()["id"]

    monkeypatch.setattr(scans_route, "nmap_available", lambda: True)
    monkeypatch.setattr(scans_route, "run_nmap", lambda target: [DiscoveredService("192.0.2.10", "lab-host", 443, "tcp", "https", "nginx")])
    started = client.post(f"/api/v1/scans/{scan_id}/start", headers=headers)
    assert started.status_code == 200
    assert started.json()["status"] == "completed"

    with SessionTesting() as session:
        asset = session.scalar(select(Asset).where(Asset.ip_address == "192.0.2.10"))
        assert asset is not None
        assert asset.asset_name == "lab-host"
