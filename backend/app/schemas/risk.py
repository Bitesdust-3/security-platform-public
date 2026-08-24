from pydantic import BaseModel


class RiskDistribution(BaseModel):
    low: int = 0
    medium: int = 0
    high: int = 0
    critical: int = 0


class RiskOverview(BaseModel):
    asset_count: int
    vulnerability_count: int
    open_vulnerability_count: int
    high_risk_count: int
    critical_risk_count: int
    risk_distribution: RiskDistribution


class RiskAssetItem(BaseModel):
    asset_id: int
    asset_name: str
    ip_address: str | None
    total_risk_score: int
    vulnerability_count: int
    highest_risk_score: int


class RiskTrendItem(BaseModel):
    date: str
    discovered: int
    fixed: int


class RiskRulesResponse(BaseModel):
    severity_score: dict[str, int]
    formula: str
    levels: dict[str, str]


class RiskSummary(BaseModel):
    asset_count: int
    vulnerability_count: int
    high_risk_vulnerability_count: int
    overall_risk_score: int


class RiskLevels(BaseModel):
    critical: int
    high: int
    medium: int
    low: int


class TopRiskAsset(BaseModel):
    ip_address: str | None
    hostname: str | None
    vulnerability_count: int
    highest_risk_level: str
    risk_score: int


class RiskTrendPoint(BaseModel):
    date: str
    vulnerability_count: int
    risk_score: int
