from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import Asset, AssetService, ScanTask, Vulnerability
from app.schemas.report import ReportCreate
from app.services.report import build_report, render_html


def test_report_uses_readable_statistics_and_real_rankings():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    asset = Asset(asset_name="测试 Web 服务器", asset_type="server", ip_address="192.0.2.50", importance=5, status="active")
    session.add(asset); session.flush()
    session.add(AssetService(asset_id=asset.id, port=443, protocol="tcp", service_name="https", service_version="2.4"))
    session.add_all([
        Vulnerability(title="严重测试漏洞", cve_id="CVE-2024-0001", severity="critical", cvss_score=9.8, status="open", asset_id=asset.id),
        Vulnerability(title="高危测试漏洞", cve_id="CVE-2024-0002", severity="high", cvss_score=8.1, status="processing", asset_id=asset.id),
        ScanTask(task_name="完成任务", target="192.0.2.50", scan_type="port_scan", status="completed"),
        ScanTask(task_name="失败任务", target="192.0.2.50", scan_type="port_scan", status="failed"),
    ])
    session.commit()
    report = build_report(session, ReportCreate(report_name="真实统计报告", period_start=datetime(2026, 1, 1), period_end=datetime(2026, 12, 31)), user_id=1)
    assert report.high_risk_vulnerability_count == 2
    assert report.top_vulnerabilities
    html = render_html(report)
    assert "扫描任务总数" in html and "高危及以上漏洞" in html
    assert "Top 高风险资产" in html and "Top 高风险漏洞" in html
    assert "CVE-2024-0001" in html
    assert "<pre>" not in html and '\"critical\"' not in html
