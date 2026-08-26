"""Security-report snapshots and presentation rendering."""

import json
from html import escape

from sqlalchemy import func, select

from app.core.time import as_shanghai, format_shanghai, to_utc_naive, utc_now_naive
from app.models import Asset, ScanResult, ScanTask, SecurityReport, Vulnerability
from app.services.risk import calculate_risk_score

RISK_LEVELS = ("critical", "high", "medium", "low")
RISK_LABELS = {"critical": "严重", "high": "高危", "medium": "中危", "low": "低危"}
VULNERABILITY_STATUS_LABELS = {"open": "待处理", "processing": "处理中", "fixed": "已修复", "ignored": "已忽略", "closed": "已关闭"}
RISK_COLOURS = {"critical": "#e5484d", "high": "#f59e0b", "medium": "#3b82f6", "low": "#22c55e"}


def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 50:
        return "high"
    if score >= 20:
        return "medium"
    return "low"


def _json(value: str | None, fallback):
    try:
        return json.loads(value or "")
    except (TypeError, ValueError):
        return fallback


def _display(value, fallback: str = "-") -> str:
    return fallback if value is None or value == "" else str(value)


def _short(value, limit: int = 60) -> str:
    """Keep data-table cells readable without changing stored vulnerability data."""
    text = _display(value)
    return text if len(text) <= limit else f"{text[:limit - 1].rstrip()}…"


def _risk_snapshot(db):
    """Use the same explainable formula as the risk-analysis API."""
    rows = db.execute(
        select(Vulnerability, Asset)
        .join(Asset, Vulnerability.asset_id == Asset.id)
        .where(Vulnerability.status.in_(["open", "processing"]), Asset.status == "active")
    ).all()
    distribution = {level: 0 for level in RISK_LEVELS}
    assets: dict[int, dict] = {}
    top_vulnerabilities: list[dict] = []
    for vulnerability, asset in rows:
        score = calculate_risk_score(vulnerability.severity, asset.importance, bool(asset.services), vulnerability.cvss_score)
        level = _risk_level(score)
        distribution[level] += 1
        item = assets.setdefault(asset.id, {"asset_id": asset.id, "asset_name": asset.asset_name or asset.hostname or asset.ip_address or "未命名资产", "ip_address": asset.ip_address, "risk_score": 0, "vulnerability_count": 0, "critical_count": 0, "high_count": 0})
        item["risk_score"] = min(100, item["risk_score"] + score)
        item["vulnerability_count"] += 1
        if level == "critical":
            item["critical_count"] += 1
        elif level == "high":
            item["high_count"] += 1
        top_vulnerabilities.append({"cve_id": vulnerability.cve_id, "title": vulnerability.title, "severity": vulnerability.severity, "risk_level": level, "risk_score": score, "cvss_score": vulnerability.cvss_score, "asset_name": item["asset_name"], "ip_address": asset.ip_address, "status": vulnerability.status, "created_at": vulnerability.created_at.isoformat() if vulnerability.created_at else ""})
    cve_count = sum(bool(item["cve_id"]) for item in top_vulnerabilities)
    top_assets = sorted(assets.values(), key=lambda item: (item["risk_score"], item["critical_count"], item["high_count"]), reverse=True)[:5]
    top_vulnerabilities.sort(key=lambda item: (item["risk_score"], item["cvss_score"] or 0, item["created_at"]), reverse=True)
    return distribution, top_assets, top_vulnerabilities[:10], cve_count


def _scan_snapshot(db, period_start, period_end) -> dict[str, int | float]:
    scans = db.scalars(select(ScanTask).where(ScanTask.created_at >= period_start, ScanTask.created_at <= period_end)).all()
    counts = {status: 0 for status in ("pending", "running", "completed", "failed", "cancelled", "archived")}
    for scan in scans:
        counts[scan.status] = counts.get(scan.status, 0) + 1
    total = len(scans)
    executed = counts["completed"] + counts["failed"]
    # Archived tasks are retained for audit history, not failed executions.
    return {"total": total, "completed": counts["completed"], "failed": counts["failed"], "running": counts["running"], "pending": counts["pending"], "cancelled": counts["cancelled"], "archived": counts["archived"], "success_rate": round(counts["completed"] / executed * 100, 2) if executed else 0}


def _recommendations(distribution: dict[str, int], scan: dict[str, int | float], db) -> list[str]:
    items: list[str] = []
    if distribution["critical"]:
        items.append(f"当前存在 {distribution['critical']} 个严重级风险项，建议立即核实受影响资产并优先制定修复或隔离方案。")
    if distribution["high"]:
        items.append(f"当前存在 {distribution['high']} 个高危风险项，建议纳入近期整改计划，并在修复后重新执行安全扫描。")
    if scan["failed"]:
        items.append("部分扫描任务未成功完成，建议检查目标连通性、扫描服务和任务执行日志后重新发起授权扫描。")
    versioned = db.scalar(select(func.count()).select_from(ScanResult).where(ScanResult.service_version.is_not(None), ScanResult.service_version != "")) or 0
    if versioned:
        items.append(f"扫描结果已识别 {versioned} 项带版本信息的服务，建议结合厂商公告评估升级、下线或访问控制措施。")
    return items or ["当前未发现高危风险项，建议持续执行周期性授权扫描并保持漏洞闭环跟踪。"]


def build_report(db, payload, user_id):
    period_start, period_end = to_utc_naive(payload.period_start), to_utc_naive(payload.period_end)
    assets = db.scalar(select(func.count()).select_from(Asset).where(Asset.status == "active")) or 0
    distribution, top_assets, top_vulnerabilities, cve_count = _risk_snapshot(db)
    vulnerability_count = sum(distribution.values())
    high_risk = distribution["critical"] + distribution["high"]
    scan = _scan_snapshot(db, period_start, period_end)
    return SecurityReport(report_name=payload.report_name, period_start=period_start, period_end=period_end, generated_at=utc_now_naive(), asset_count=assets, online_asset_count=assets, high_risk_asset_count=sum(item["risk_score"] >= 50 for item in top_assets), vulnerability_count=vulnerability_count, cve_count=cve_count, high_risk_vulnerability_count=high_risk, risk_distribution=json.dumps(distribution), scan_statistics=json.dumps(scan), vulnerability_trend=json.dumps([]), top_risk_assets=json.dumps(top_assets), top_vulnerabilities=json.dumps(top_vulnerabilities), recommendations=json.dumps(_recommendations(distribution, scan, db)), created_by=user_id)


def as_dict(report):
    data = {"id": report.id, "report_name": report.report_name, "period_start": as_shanghai(report.period_start), "period_end": as_shanghai(report.period_end), "generated_at": as_shanghai(report.generated_at), "asset_count": report.asset_count, "online_asset_count": report.online_asset_count, "high_risk_asset_count": report.high_risk_asset_count, "vulnerability_count": report.vulnerability_count, "cve_count": report.cve_count, "high_risk_vulnerability_count": report.high_risk_vulnerability_count, "created_by": report.created_by, "status": report.status, "archived_at": as_shanghai(report.archived_at)}
    for key, fallback in (("risk_distribution", {}), ("scan_statistics", {}), ("vulnerability_trend", []), ("top_risk_assets", []), ("top_vulnerabilities", []), ("recommendations", [])):
        data[key] = _json(getattr(report, key, None), fallback)
    return data


def _ring_chart(distribution: dict[str, int]) -> str:
    total = sum(int(distribution.get(level, 0) or 0) for level in RISK_LEVELS)
    if not total:
        return "<div class='chart-empty'>当前统计周期内暂无待处理风险项</div>"
    offset, circles = 0, []
    for level in RISK_LEVELS:
        value = int(distribution.get(level, 0) or 0)
        if not value:
            continue
        length = value / total * 100
        circles.append(f"<circle cx='90' cy='90' r='62' fill='none' stroke-width='18' pathLength='100' transform='rotate(-90 90 90)' stroke='{RISK_COLOURS[level]}' stroke-dasharray='{length:.4f} {100 - length:.4f}' stroke-dashoffset='{-offset:.4f}' />")
        offset += length
    return "<svg class='ring-chart' viewBox='0 0 180 180' role='img' aria-label='风险等级分布图'><circle cx='90' cy='90' r='62' fill='none' stroke='#e7eef2' stroke-width='18' />" + "".join(circles) + f"<text x='90' y='84' text-anchor='middle' font-size='28' font-weight='bold' fill='#123b5a'>{total}</text><text x='90' y='106' text-anchor='middle' font-size='12' fill='#668095'>风险项</text></svg>"


def _table(headers: list[str], rows: list[list[str]], empty_message: str, css_class: str = "") -> str:
    if not rows:
        return f"<div class='empty'>{escape(empty_message)}</div>"
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    return f"<table class='{css_class}'><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_html(report):
    d = as_dict(report)
    distribution = {level: int(d["risk_distribution"].get(level, 0) or 0) for level in RISK_LEVELS}
    scan = d["scan_statistics"]
    high_ratio = report.high_risk_vulnerability_count / report.vulnerability_count * 100 if report.vulnerability_count else 0
    distribution_rows = [[f"<span class='dot dot-{level}'></span>{RISK_LABELS[level]}", str(distribution[level])] for level in RISK_LEVELS]
    asset_rows = [[escape(_display(item.get("asset_name"))), escape(_display(item.get("ip_address"))), str(item.get("critical_count", 0)), str(item.get("high_count", 0)), str(item.get("vulnerability_count", 0)), f"<span class='risk-pill'>{item.get('risk_score', 0)} 分</span>"] for item in d["top_risk_assets"]]
    vulnerability_rows = []
    for item in d["top_vulnerabilities"]:
        level = item.get("risk_level", "low")
        vulnerability_rows.append([escape(_display(item.get("cve_id"))), escape(_short(item.get("title"))), f"<span class='severity severity-{level}'>{RISK_LABELS.get(level, '低危')}</span>", escape(_display(item.get("cvss_score"))), escape(f"{_display(item.get('asset_name'))} / {_display(item.get('ip_address'))}"), escape(VULNERABILITY_STATUS_LABELS.get(item.get("status"), "-"))])
    scan_cards = "".join(f"<div class='scan-card'><span>{label}</span><strong>{value}</strong></div>" for label, value in (("扫描任务总数", scan.get("total", 0)), ("已完成扫描", scan.get("completed", 0)), ("失败扫描", scan.get("failed", 0)), ("执行中", scan.get("running", 0)), ("等待执行", scan.get("pending", 0)), ("已归档", scan.get("archived", 0)), ("扫描成功率", f"{float(scan.get('success_rate', 0)):.2f}%")))
    recommendations = "".join(f"<li>{escape(_display(item))}</li>" for item in d["recommendations"])
    return f"""<!doctype html><html lang='zh-CN'><head><meta charset='utf-8'><style>
@font-face{{font-family:'SecureOps CJK';src:url('file:///usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc');}}@page{{size:A4;margin:16mm 15mm 18mm;@bottom-center{{content:'SecureOps 安全运营报告 · 第 ' counter(page) ' 页';font-family:'SecureOps CJK';font-size:9px;color:#64748b;}}}}*{{box-sizing:border-box}}body{{font-family:'SecureOps CJK','Noto Sans CJK SC',sans-serif;color:#183047;font-size:10.5pt;line-height:1.55;margin:0}}.cover{{min-height:235mm;padding:31mm 20mm;background:linear-gradient(145deg,#071c34,#0b355a 58%,#057b9f);color:#effbff;page-break-after:always;position:relative}}.cover:after{{content:'';position:absolute;right:20mm;bottom:21mm;width:65mm;height:65mm;border:1.5px solid #35d3e6;border-radius:50%;opacity:.55;box-shadow:0 0 0 12mm rgba(53,211,230,.07),0 0 0 24mm rgba(53,211,230,.05)}}.eyebrow{{color:#53e3ef;font-size:10pt;letter-spacing:2px;font-weight:bold}}.cover h1{{font-size:31pt;line-height:1.25;margin:13mm 0 4mm}}.subtitle{{font-size:15pt;color:#bce9f4}}.cover-meta{{margin-top:105mm;color:#d3edf5;font-size:10.5pt}}.brand{{font-size:15pt;font-weight:bold;letter-spacing:1px}}h2{{color:#0b4e78;font-size:17pt;border-left:4px solid #13b8cf;padding-left:10px;margin:11mm 0 5mm}}.section{{break-inside:avoid;margin-bottom:9mm}}.intro{{color:#536b7f;margin:0 0 7mm}}.metrics{{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm}}.metric{{border:1px solid #d6e6ee;border-radius:4px;padding:4mm;background:#f7fbfd;min-height:25mm}}.metric span,.scan-card span{{display:block;color:#5e7487;font-size:9pt}}.metric strong{{font-size:21pt;line-height:1.3;color:#063e64}}.metric.alert strong{{color:#d04343}}.risk-layout{{display:grid;grid-template-columns:1fr 1fr;gap:8mm;align-items:center}}.chart-wrap{{text-align:center}}.ring-chart{{width:53mm;height:53mm}}.dot{{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:6px}}.dot-critical{{background:#e5484d}}.dot-high{{background:#f59e0b}}.dot-medium{{background:#3b82f6}}.dot-low{{background:#22c55e}}table{{width:100%;border-collapse:collapse;font-size:9.1pt;table-layout:fixed}}tr{{break-inside:avoid;page-break-inside:avoid}}th{{background:#0b466d;color:#fff;font-weight:normal;padding:2.5mm 2mm;text-align:left}}td{{padding:2.3mm 2mm;border-bottom:1px solid #dce7ed;vertical-align:top;word-break:break-word}}tr:nth-child(even) td{{background:#f6fafc}}.severity{{display:inline-block;padding:1px 6px;border-radius:9px;font-size:8.4pt;white-space:nowrap}}.severity-critical{{background:#fde7e7;color:#ad252b}}.severity-high{{background:#fff2d8;color:#a76000}}.severity-medium{{background:#e5f0ff;color:#1b62b0}}.severity-low{{background:#e2f6e9;color:#197341}}.risk-pill{{font-weight:bold;color:#0b4e78;white-space:nowrap}}.scan-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:3mm}}.scan-card{{border:1px solid #d6e6ee;border-radius:4px;padding:3.5mm;background:#f8fbfd}}.scan-card strong{{font-size:16pt;color:#084d76}}.recommendations{{margin:0;padding-left:6mm}}.recommendations li{{margin-bottom:2.5mm;padding-left:1mm}}.empty,.chart-empty{{padding:8mm;text-align:center;color:#718497;background:#f7fafc;border:1px dashed #cbdbe5;border-radius:4px}}.small-table td{{padding:2.2mm 3mm}}.summary-note{{margin-top:4mm;color:#416078;font-size:9.4pt}}</style></head><body>
<section class='cover'><div class='eyebrow'>SECUREOPS · SECURITY OPERATIONS CENTER</div><h1>安全运营报告</h1><div class='subtitle'>{escape(report.report_name)}</div><div class='cover-meta'><div class='brand'>SecureOps</div><div>报告生成时间：{escape(format_shanghai(report.generated_at))}</div><div>统计周期：{escape(format_shanghai(report.period_start))} 至 {escape(format_shanghai(report.period_end))}</div></div></section>
<section class='section'><h2>安全概览</h2><p class='intro'>本报告基于当前 SecureOps 平台中已登记资产、待处理漏洞和扫描任务的真实数据生成。</p><div class='metrics'><div class='metric'><span>管理资产</span><strong>{report.asset_count}</strong></div><div class='metric'><span>待处理漏洞</span><strong>{report.vulnerability_count}</strong></div><div class='metric'><span>CVE 编号漏洞</span><strong>{report.cve_count}</strong></div><div class='metric alert'><span>高危及以上</span><strong>{report.high_risk_vulnerability_count}</strong></div></div></section>
<section class='section'><h2>风险等级分布</h2><div class='risk-layout'><div class='chart-wrap'>{_ring_chart(distribution)}</div><div>{_table(['风险等级','数量'], distribution_rows, '暂无风险等级统计', 'small-table')}<p class='summary-note'>高危及以上漏洞：<b>{report.high_risk_vulnerability_count}</b> 项，占待处理漏洞的 <b>{high_ratio:.2f}%</b>。</p></div></div></section>
<section class='section'><h2>Top 高风险资产</h2>{_table(['资产名称','IP 地址','严重','高危','漏洞总数','风险评分'], asset_rows, '暂无高风险资产')}</section><section class='section'><h2>Top 高风险漏洞</h2>{_table(['CVE 编号','漏洞名称','风险等级','CVSS','受影响资产','当前状态'], vulnerability_rows, '暂无待处理高风险漏洞')}</section><section class='section'><h2>扫描任务情况</h2><div class='scan-grid'>{scan_cards}</div></section><section class='section'><h2>整改建议</h2><ul class='recommendations'>{recommendations}</ul></section></body></html>"""
