from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.dependencies import get_db
from app.main import app
from app.models import security  # noqa: F401

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_register_login_and_me():
    username = "auth-test-user"
    registration = client.post("/api/v1/auth/register", json={"username": username, "email": "auth-test@example.com", "password": "safe-password-123"})
    assert registration.status_code == 201
    assert "hashed_password" not in registration.json()

    login = client.post("/api/v1/auth/login", json={"username": username, "password": "safe-password-123"})
    assert login.status_code == 200
    token = login.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["username"] == username


def test_me_requires_authentication():
    assert client.get("/api/v1/auth/me").status_code == 401
