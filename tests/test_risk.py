from app.api.routes.risk import risk_level


def test_risk_level_boundaries():
    assert risk_level(19) == "low"
    assert risk_level(20) == "medium"
    assert risk_level(50) == "high"
    assert risk_level(80) == "critical"
