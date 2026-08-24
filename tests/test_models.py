from app.db.base import Base
from app.models import Asset, AssetService, AssetVulnerability, ScanTask, User, Vulnerability


def test_core_tables_are_registered():
    expected = {"users", "assets", "asset_services", "scan_tasks", "vulnerabilities", "asset_vulnerabilities"}

    assert expected.issubset(Base.metadata.tables)
    assert Asset.__tablename__ == "assets"
    assert AssetService.__tablename__ == "asset_services"
    assert AssetVulnerability.__tablename__ == "asset_vulnerabilities"
    assert ScanTask.__tablename__ == "scan_tasks"
    assert User.__tablename__ == "users"
    assert Vulnerability.__tablename__ == "vulnerabilities"
