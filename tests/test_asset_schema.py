import pytest

from app.schemas.asset import AssetCreate, AssetServiceCreate


def test_asset_schema_accepts_valid_ip():
    asset = AssetCreate(asset_name="web-01", asset_type="server", ip_address="192.0.2.10")

    assert str(asset.ip_address) == "192.0.2.10"


def test_asset_schema_rejects_invalid_port():
    with pytest.raises(ValueError):
        AssetServiceCreate(port=70000, protocol="tcp")
