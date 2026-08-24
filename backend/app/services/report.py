import json
from datetime import datetime, timezone
from sqlalchemy import func, select
from app.models import Asset, AssetVulnerability, ScanTask, SecurityReport, Vulnerability
def risk_level(score): return "critical" if score >= 80 else "high" if score >= 50 else "medium" if score >= 20 else "low"

def build_report(db, payload, user_id):
    assets = db.scalar(select(func.count()).select_from(Asset)) or 0
    online = db.scalar(select(func.count()).select_from(Asset).where(Asset.status == "active")) or 0
    vulns = db.scalars(select(Vulnerability).where(Vulnerability.status.in_(["open", "processing"]))).all()
    dist={x:0 for x in ("critical","high","medium","low")}; high=0
    for v in vulns:
        score=(v.cvss_score or 0)*3 + {"critical":60,"high":45,"medium":25,"low":10,"info":0}.get(v.severity,0)
        level=risk_level(min(100,int(score))); dist[level]+=1; high += level in {"high","critical"}
    scans = db.scalars(select(ScanTask).where(ScanTask.created_at >= payload.period_start, ScanTask.created_at <= payload.period_end)).all()
    total_scans=len(scans); completed=sum(s.status=="completed" for s in scans)
    top=[]
    rows=db.execute(select(Asset.id,Asset.ip_address,Asset.hostname,func.sum(AssetVulnerability.risk_score),func.count(AssetVulnerability.id)).join(AssetVulnerability,AssetVulnerability.asset_id==Asset.id).group_by(Asset.id,Asset.ip_address,Asset.hostname).order_by(func.sum(AssetVulnerability.risk_score).desc()).limit(10)).all()
    for r in rows: top.append({"asset_id":r[0],"ip_address":r[1],"hostname":r[2],"risk_score":int(r[3] or 0),"vulnerability_count":int(r[4])})
    recommendations=[]
    if dist["critical"]: recommendations.append("优先处理 Critical 级别漏洞并核实受影响资产")
    if dist["high"]: recommendations.append("制定 High 级别漏洞整改计划并跟踪复测")
    if not recommendations: recommendations.append("当前未发现高危风险，建议保持周期巡检")
    return SecurityReport(report_name=payload.report_name,period_start=payload.period_start,period_end=payload.period_end,generated_at=datetime.now(timezone.utc),asset_count=assets,online_asset_count=online,high_risk_asset_count=len([x for x in top if x["risk_score"]>=50]),vulnerability_count=len(vulns),cve_count=sum(bool(v.cve_id) for v in vulns),high_risk_vulnerability_count=high,risk_distribution=json.dumps(dist),scan_statistics=json.dumps({"total":total_scans,"completed":completed,"success_rate":round(completed/total_scans*100,2) if total_scans else 0}),vulnerability_trend=json.dumps([]),top_risk_assets=json.dumps(top),recommendations=json.dumps(recommendations),created_by=user_id)

def as_dict(report):
    data={"id":report.id,"report_name":report.report_name,"period_start":report.period_start,"period_end":report.period_end,"generated_at":report.generated_at,"asset_count":report.asset_count,"online_asset_count":report.online_asset_count,"high_risk_asset_count":report.high_risk_asset_count,"vulnerability_count":report.vulnerability_count,"cve_count":report.cve_count,"high_risk_vulnerability_count":report.high_risk_vulnerability_count,"created_by":report.created_by}
    for key in ("risk_distribution","scan_statistics","vulnerability_trend","top_risk_assets","recommendations"): data[key]=json.loads(getattr(report,key) or "{}")
    return data

def render_html(report):
    d=as_dict(report); return f"""<!doctype html><html><head><meta charset='utf-8'><style>body{{font-family:Arial,'Microsoft YaHei';color:#172033;padding:40px}}h1{{color:#1261a0}}.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}}.card{{padding:18px;background:#eef7ff;border-radius:8px}}table{{width:100%;border-collapse:collapse;margin-top:20px}}th,td{{padding:10px;border-bottom:1px solid #ddd;text-align:left}}</style></head><body><h1>{report.report_name}</h1><p>统计周期：{report.period_start} 至 {report.period_end}</p><div class='grid'><div class='card'>资产总数<br><b>{report.asset_count}</b></div><div class='card'>漏洞总数<br><b>{report.vulnerability_count}</b></div><div class='card'>CVE 数量<br><b>{report.cve_count}</b></div><div class='card'>高危漏洞<br><b>{report.high_risk_vulnerability_count}</b></div></div><h2>风险等级分布</h2><pre>{json.dumps(d['risk_distribution'],ensure_ascii=False,indent=2)}</pre><h2>扫描情况</h2><pre>{json.dumps(d['scan_statistics'],ensure_ascii=False,indent=2)}</pre><h2>整改建议</h2><ul>{''.join(f'<li>{x}</li>' for x in d['recommendations'])}</ul></body></html>"""
