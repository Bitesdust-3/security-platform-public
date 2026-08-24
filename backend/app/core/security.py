from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from app.core.config import settings

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_digest: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_digest.encode("utf-8"))


def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY 未配置")
    lifetime = expires_minutes or settings.access_token_expire_minutes
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=lifetime)
    payload: dict[str, Any] = {"sub": subject, "exp": expires_at}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    if not settings.jwt_secret_key:
        raise RuntimeError("JWT_SECRET_KEY 未配置")
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
