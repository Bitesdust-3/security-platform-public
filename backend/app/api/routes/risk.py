from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.models import Asset, AssetVulnerability, ScanResult, ScanTask, Vulnerability
from app.schemas.risk import RiskAssetItem, RiskDistribution, RiskLevels, RiskOverview, RiskRulesResponse, RiskSummary, RiskTrendItem, RiskTrendPoint, TopRiskAsset
from app.services.risk import RISK_LEVELS, SEVERITY_SCORE, calculate_risk_score

router = APIRouter(prefix="/risk")


def _is_admin(user: CurrentUser) -> bool:
    return any(role.name == "admin" for role in user.roles)


def _authorized_asset_ids(user: CurrentUser, db: DbSession) -> set[int] | None:
    if _is_admin(user):
        return None
    rows = db.scalars(select(ScanResult.asset_id).join(ScanTask, ScanTask.id == ScanResult.scan_task_id).where(ScanTask.created_by == user.id, ScanResult.asset_id.is_not(None))).all()
    return {int(asset_id) for asset_id in rows if asset_id is not None}


def _risk_records(user: CurrentUser, db: DbSession) -> list[tuple[Vulnerability, Asset, int]]:
    authorized = _authorized_asset_ids(user, db)
    query = select(Vulnerability, Asset).join(Asset, Vulnerability.asset_id == Asset.id).where(Vulnerability.status.in_(["open", "processing"]))
    if authorized is not None:
        if not authorized:
            return []
        query = query.where(Vulnerability.asset_id.in_(authorized))
    records = []
    for vulnerability, asset in db.execute(query).all():
        has_service = bool(asset.services)
        score = calculate_risk_score(vulnerability.severity, asset.importance, has_service, vulnerability.cvss_score)
        records.append((vulnerability, asset, score))
    return records


def risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


@router.get("/summary", response_model=RiskSummary, summary="风险摘要")
def risk_summary(user: CurrentUser, db: DbSession) -> RiskSummary:
    records = _risk_records(user, db)
    asset_ids = {asset.id for _, asset, _ in records}
    scores = [score for _, _, score in records]
    return RiskSummary(asset_count=len(asset_ids), vulnerability_count=len(records), high_risk_vulnerability_count=sum(risk_level(score) in {"high", "critical"} for score in scores), overall_risk_score=min(100, sum(scores)))


@router.get("/levels", response_model=RiskLevels, summary="风险等级汇总")
def risk_levels(user: CurrentUser, db: DbSession) -> RiskLevels:
    counts = {level: 0 for level in ("critical", "high", "medium", "low")}
    for _, _, score in _risk_records(user, db):
        counts[risk_level(score)] += 1
    return RiskLevels(**counts)


@router.get("/top-assets", response_model=list[TopRiskAsset], summary="高风险资产排行")
def top_risk_assets(user: CurrentUser, db: DbSession, limit: int = Query(10, ge=1, le=100)) -> list[TopRiskAsset]:
    grouped: dict[int, list[tuple[Vulnerability, Asset, int]]] = {}
    for record in _risk_records(user, db):
        grouped.setdefault(record[1].id, []).append(record)
    ranked = sorted(grouped.values(), key=lambda values: sum(item[2] for item in values), reverse=True)[:limit]
    return [TopRiskAsset(ip_address=items[0][1].ip_address, hostname=items[0][1].hostname, vulnerability_count=len(items), highest_risk_level=risk_level(max(item[2] for item in items)), risk_score=min(100, sum(item[2] for item in items))) for items in ranked]


@router.get("/overview", response_model=RiskOverview, summary="风险总览")
def risk_overview(_: CurrentUser, db: DbSession) -> RiskOverview:
    # Dashboard inventory follows the asset list: inactive (soft-deleted)
    # assets are retained for history but excluded from the active total.
    asset_count = db.scalar(select(func.count()).select_from(Asset).where(Asset.status == "active")) or 0
    vulnerability_count = db.scalar(select(func.count()).select_from(Vulnerability)) or 0
    open_filter = AssetVulnerability.status.in_(["open", "in_progress"])
    open_count = db.scalar(select(func.count()).select_from(AssetVulnerability).where(open_filter)) or 0
    links = db.scalars(select(AssetVulnerability).where(open_filter)).all()
    distribution = {level: 0 for level in RISK_LEVELS}
    for link in links:
        distribution[risk_level(link.risk_score)] += 1
    return RiskOverview(asset_count=asset_count, vulnerability_count=vulnerability_count, open_vulnerability_count=open_count, high_risk_count=distribution["high"] + distribution["critical"], critical_risk_count=distribution["critical"], risk_distribution=RiskDistribution(**distribution))


@router.get("/assets", response_model=list[RiskAssetItem], summary="高风险资产排名")
def risk_assets(_: CurrentUser, db: DbSession, limit: int = Query(10, ge=1, le=100)) -> list[RiskAssetItem]:
    rows = db.execute(select(Asset.id, Asset.asset_name, Asset.ip_address, func.sum(AssetVulnerability.risk_score), func.count(AssetVulnerability.id), func.max(AssetVulnerability.risk_score)).join(AssetVulnerability, AssetVulnerability.asset_id == Asset.id).where(AssetVulnerability.status.in_(["open", "in_progress"])).group_by(Asset.id, Asset.asset_name, Asset.ip_address).order_by(func.sum(AssetVulnerability.risk_score).desc()).limit(limit)).all()
    return [RiskAssetItem(asset_id=row[0], asset_name=row[1], ip_address=row[2], total_risk_score=int(row[3] or 0), vulnerability_count=int(row[4]), highest_risk_score=int(row[5] or 0)) for row in rows]


@router.get("/trend", response_model=list[RiskTrendPoint], summary="风险趋势")
def risk_trend(user: CurrentUser, db: DbSession, days: int = Query(30, ge=7, le=90)) -> list[RiskTrendPoint]:
    start = datetime.now(timezone.utc) - timedelta(days=days)
    records = []
    for record in _risk_records(user, db):
        created_at = record[0].created_at
        if created_at and created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if created_at and created_at >= start:
            records.append(record)
    grouped: dict[str, list[int]] = {}
    for vulnerability, _, score in records:
        day = vulnerability.created_at.date().isoformat()
        grouped.setdefault(day, []).append(score)
    return [RiskTrendPoint(date=day, vulnerability_count=len(scores), risk_score=min(100, sum(scores))) for day, scores in sorted(grouped.items())]


@router.get("/rules", response_model=RiskRulesResponse, summary="风险评分规则")
def risk_rules(_: CurrentUser) -> RiskRulesResponse:
    return RiskRulesResponse(severity_score=SEVERITY_SCORE, formula="漏洞严重性分数 + 资产重要性 × 2 + 开放服务加分 10，结果限制在 0—100", levels=RISK_LEVELS)
