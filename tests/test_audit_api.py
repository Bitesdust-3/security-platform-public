from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import AuditLog, Role, User

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)
db = SessionTesting()
role = Role(name="admin", description="管理员")
db.add(role)
db.flush()
db.add(User(username="audit-admin", email="audit-admin@example.com", hashed_password=hash_password("audit-password-123"), roles=[role]))
db.add(AuditLog(user_id=None, action="test", resource="system", resource_type="system", description="测试审计", detail="测试审计"))
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


def test_audit_logs_require_admin():
    app.dependency_overrides[get_db] = override_get_db
    login = client.post("/api/v1/auth/login", json={"username": "audit-admin", "password": "audit-password-123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    response = client.get("/api/v1/audit/logs?page=1&page_size=10", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] >= 1
    assert response.json()["data"][0]["description"]
