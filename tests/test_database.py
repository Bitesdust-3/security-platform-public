from sqlalchemy import create_engine, inspect, text

from app.db.base import Base
from app.models import Asset, Role, User, Vulnerability  # noqa: F401


def test_sqlalchemy_connection_and_metadata():
    engine = create_engine("sqlite:///:memory:")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT 1")).scalar_one() == 1
    Base.metadata.create_all(engine)
    tables = set(inspect(engine).get_table_names())
    assert {"users", "roles", "assets", "vulnerabilities"}.issubset(tables)
