from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import Role, User

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)
db = SessionTesting()
admin_role = Role(name="admin", description="管理员")
user_role = Role(name="user", description="普通用户")
db.add_all([admin_role, user_role])
db.add(User(username="asset-admin", email="asset-admin@example.com", hashed_password=hash_password("admin-password-123"), roles=[admin_role]))
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


def token(username: str, password: str) -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_asset_crud_and_permissions():
    app.dependency_overrides[get_db] = override_get_db
    admin_token = token("asset-admin", "admin-password-123")
    normal_register = client.post("/api/v1/auth/register", json={"username": "asset-user", "email": "asset-user@example.com", "password": "user-password-123"})
    assert normal_register.status_code == 201
    user_token = token("asset-user", "user-password-123")

    created = client.post("/api/v1/assets", headers={"Authorization": f"Bearer {admin_token}"}, json={"asset_name": "web-01", "ip_address": "192.0.2.10", "hostname": "web-01.lab", "asset_type": "server", "status": "active", "os_info": "Linux", "description": "test"})
    assert created.status_code == 201
    asset_id = created.json()["id"]
    assert client.post("/api/v1/assets", headers={"Authorization": f"Bearer {user_token}"}, json={"asset_name": "denied", "asset_type": "server"}).status_code == 403

    listed = client.get("/api/v1/assets?ip_address=192.0.2&page=1&page_size=10", headers={"Authorization": f"Bearer {user_token}"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    assert listed.json()["data"][0]["asset_name"] == "web-01"

    updated = client.put(f"/api/v1/assets/{asset_id}", headers={"Authorization": f"Bearer {admin_token}"}, json={"asset_name": "web-01-updated", "ip_address": "192.0.2.10", "asset_type": "server", "status": "active"})
    assert updated.status_code == 200
    assert updated.json()["asset_name"] == "web-01-updated"

    deleted = client.delete(f"/api/v1/assets/{asset_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert deleted.status_code == 204
    detail = client.get(f"/api/v1/assets/{asset_id}", headers={"Authorization": f"Bearer {user_token}"})
    assert detail.status_code == 200
    assert detail.json()["status"] == "inactive"
