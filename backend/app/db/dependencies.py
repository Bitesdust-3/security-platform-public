from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database import get_db as database_get_db


def get_db() -> Generator[Session, None, None]:
    yield from database_get_db()
