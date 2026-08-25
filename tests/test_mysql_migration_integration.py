import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text


@pytest.mark.integration
def test_mysql_upgrade_head_creates_complete_schema():
    database_url = os.getenv("MYSQL_TEST_DATABASE_URL")
    if not database_url:
        pytest.skip("set MYSQL_TEST_DATABASE_URL to run the MySQL migration integration test")

    backend = Path(__file__).resolve().parents[1] / "backend"
    env = os.environ | {
        "DATABASE_URL": database_url,
        "ENVIRONMENT": "test",
        "PYTHONPATH": str(backend),
    }
    subprocess.run(["alembic", "upgrade", "head"], cwd=backend, env=env, check=True)

    engine = create_engine(database_url, pool_pre_ping=True)
    required = {"users", "assets", "scan_tasks", "scan_results", "vulnerabilities", "cve_intelligence", "scan_schedules", "security_reports", "audit_logs"}
    assert required.issubset(set(inspect(engine).get_table_names()))
    with engine.connect() as connection:
        assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "f5a6b7c8d9e0"
