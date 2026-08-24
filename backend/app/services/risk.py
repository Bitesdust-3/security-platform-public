SEVERITY_SCORE = {"info": 0, "low": 10, "medium": 25, "high": 45, "critical": 60}
RISK_LEVELS = {"low": "0-19", "medium": "20-49", "high": "50-79", "critical": "80-100"}


def calculate_risk_score(severity: str, asset_importance: int, has_service: bool, cvss_score: float | None = None) -> int:
    """Explainable score = severity base + CVSS*3 + asset importance*2 + service bonus."""
    score = SEVERITY_SCORE.get(severity, 0) + (cvss_score or 0) * 3 + asset_importance * 2 + (10 if has_service else 0)
    # Keep the public risk score integral and deterministic for API schemas
    # while preserving the documented explainable formula.
    return int(min(100, max(0, round(score))))
