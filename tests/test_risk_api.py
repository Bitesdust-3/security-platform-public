from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import Asset, Role, ScanResult, ScanTask, User, Vulnerability
from app.services.risk import calculate_risk_score

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)
db = SessionTesting()
admin_role, user_role = Role(name="admin"), Role(name="user")
admin = User(username="risk-admin", email="risk-admin@example.com", hashed_password=hash_password("risk-password-123"), roles=[admin_role])
normal = User(username="risk-user", email="risk-user@example.com", hashed_password=hash_password("risk-user-password-123"), roles=[user_role])
asset = Asset(asset_name="risk-web", ip_address="192.0.2.30", hostname="risk-web.lab", asset_type="server", importance=5, status="active")
db.add_all([admin_role, user_role, admin, normal, asset])
db.flush()
task = ScanTask(task_name="risk scan", target="192.0.2.30", scan_type="port_scan", created_by=normal.id, status="completed")
db.add(task)
db.flush()
db.add(ScanResult(scan_task_id=task.id, asset_id=asset.id, result_type="service", normalized_data="192.0.2.30:443/tcp"))
db.add(Vulnerability(title="Critical test", severity="critical", cvss_score=9.0, status="open", asset_id=asset.id, scan_task_id=task.id))
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


def get_token(username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_risk_formula_and_permission_scope():
    assert calculate_risk_score("critical", 5, True, 9.0) == 100
    app.dependency_overrides[get_db] = override_get_db
    admin_headers = {"Authorization": f"Bearer {get_token('risk-admin', 'risk-password-123')}"}
    user_headers = {"Authorization": f"Bearer {get_token('risk-user', 'risk-user-password-123')}"}
    summary = client.get("/api/v1/risk/summary", headers=admin_headers)
    assert summary.status_code == 200
    assert summary.json()["vulnerability_count"] == 1
    assert client.get("/api/v1/risk/levels", headers=user_headers).json()["critical"] == 1
    assert client.get("/api/v1/risk/top-assets", headers=user_headers).json()[0]["risk_score"] == 97


def test_risk_requires_authentication():
    app.dependency_overrides[get_db] = override_get_db
    assert client.get("/api/v1/risk/summary").status_code == 401
