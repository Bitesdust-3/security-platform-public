"""Idempotent seed data for the isolated SecureOps demo environment only."""

import json
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import (
    Asset,
    AssetService,
    AssetVulnerability,
    Role,
    ScanResult,
    ScanTask,
    SecurityReport,
    User,
    Vulnerability,
)


DEMO_MARKER = "[DEMO-V2]"


def _assert_demo_database() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    database_name = make_url(database_url).database or ""
    if not database_name.endswith("_demo"):
        raise RuntimeError("Demo数据只能写入名称以 _demo 结尾的独立数据库")
    if os.environ.get("ALLOW_DEMO_SEED", "false").lower() != "true":
        raise RuntimeError("必须显式设置 ALLOW_DEMO_SEED=true")


def seed_demo_v2() -> None:
    _assert_demo_database()
    password = os.environ.get("DEMO_ADMIN_PASSWORD")
    if not password:
        raise RuntimeError("DEMO_ADMIN_PASSWORD不能为空")

    db = SessionLocal()
    try:
        admin_role = db.scalar(select(Role).where(Role.name == "admin"))
        if admin_role is None:
            admin_role = Role(name="admin", description="Demo管理员")
            db.add(admin_role)
            db.flush()
        user_role = db.scalar(select(Role).where(Role.name == "user"))
        if user_role is None:
            db.add(Role(name="user", description="Demo只读用户"))

        username = os.environ.get("DEMO_ADMIN_USERNAME", "demo-admin")
        admin = db.scalar(select(User).where(User.username == username))
        if admin is None:
            admin = User(
                username=username,
                email="demo-admin@secureops.local",
                display_name="SecureOps Demo Admin",
                hashed_password=hash_password(password),
                is_active=True,
                roles=[admin_role],
            )
            db.add(admin)
            db.flush()

        existing = db.scalar(select(Asset.id).where(Asset.description == DEMO_MARKER).limit(1))
        if existing is not None:
            print("SecureOps Demo V2 数据已存在，跳过重复初始化")
            return

        assets = [
            Asset(asset_name="DEMO Web Gateway", ip_address="10.10.10.11", hostname="demo-web-01", asset_type="server", importance=5, status="active", os_info="Ubuntu 22.04 / Nginx", environment="demo", description=DEMO_MARKER),
            Asset(asset_name="DEMO Database", ip_address="10.10.10.21", hostname="demo-db-01", asset_type="database", importance=5, status="active", os_info="Rocky Linux 9 / MySQL", environment="demo", description=DEMO_MARKER),
            Asset(asset_name="DEMO Linux App", ip_address="10.10.10.31", hostname="demo-app-01", asset_type="server", importance=4, status="active", os_info="Ubuntu 20.04", environment="demo", description=DEMO_MARKER),
            Asset(asset_name="DEMO Operations Host", ip_address="10.10.10.41", hostname="demo-ops-01", asset_type="workstation", importance=3, status="active", os_info="Debian 12", environment="demo", description=DEMO_MARKER),
            Asset(asset_name="DEMO Network Device", ip_address="10.10.10.51", hostname="demo-edge-01", asset_type="network_device", importance=3, status="active", os_info="Network OS", environment="demo", description=DEMO_MARKER),
        ]
        db.add_all(assets)
        db.flush()

        services = [
            AssetService(asset_id=assets[0].id, port=443, protocol="tcp", service_name="nginx", service_version="1.24.0"),
            AssetService(asset_id=assets[0].id, port=22, protocol="tcp", service_name="OpenSSH", service_version="8.9"),
            AssetService(asset_id=assets[1].id, port=3306, protocol="tcp", service_name="MySQL", service_version="8.0"),
            AssetService(asset_id=assets[2].id, port=8080, protocol="tcp", service_name="Apache Tomcat", service_version="9.0"),
            AssetService(asset_id=assets[3].id, port=22, protocol="tcp", service_name="OpenSSH", service_version="9.2"),
        ]
        db.add_all(services)

        vulnerability_specs = [
            ("CVE-2024-6387", "OpenSSH regreSSHion候选风险", "critical", 9.8, assets[0], "open", 94),
            ("CVE-2021-41773", "Apache路径穿越候选风险", "critical", 9.8, assets[2], "open", 88),
            ("CVE-2023-44487", "HTTP/2 Rapid Reset候选风险", "high", 8.6, assets[0], "processing", 76),
            ("CVE-2023-38545", "libcurl堆溢出候选风险", "high", 8.1, assets[3], "open", 68),
            ("CVE-2022-0778", "OpenSSL无限循环候选风险", "high", 7.5, assets[1], "open", 58),
            ("CVE-2023-22515", "应用访问控制候选风险", "medium", 6.5, assets[2], "processing", 42),
            ("CVE-2022-27926", "邮件服务输入校验风险", "medium", 5.3, assets[4], "open", 32),
            ("CVE-2021-3156", "本地权限配置候选风险", "low", 3.7, assets[3], "open", 18),
        ]
        vulnerabilities = []
        for cve_id, title, severity, cvss, asset, status, score in vulnerability_specs:
            vulnerability = Vulnerability(
                title=f"{DEMO_MARKER} {title}", cve_id=cve_id,
                description="仅用于SecureOps独立Demo环境的候选漏洞数据",
                severity=severity, cvss_score=cvss, status=status,
                asset_id=asset.id, source="demo-v2",
                remediation="在授权环境中核实版本，并按照厂商安全公告升级或缓解。",
            )
            db.add(vulnerability)
            db.flush()
            vulnerabilities.append(vulnerability)
            db.add(AssetVulnerability(
                asset_id=asset.id, vulnerability_id=vulnerability.id,
                status="in_progress" if status == "processing" else "open",
                risk_score=score, first_seen_at=datetime.now(timezone.utc) - timedelta(days=7),
                last_seen_at=datetime.now(timezone.utc),
                verification_note=DEMO_MARKER,
            ))

        now = datetime.now(timezone.utc)
        scans = [
            ScanTask(task_name=f"{DEMO_MARKER} Web服务授权巡检", target="10.10.10.11", scan_type="port_scan", status="completed", result_summary="发现2条开放服务，匹配3条候选CVE", created_by=admin.id, started_at=now - timedelta(minutes=18), finished_at=now - timedelta(minutes=17)),
            ScanTask(task_name=f"{DEMO_MARKER} Linux主机巡检", target="10.10.10.31", scan_type="port_scan", status="running", result_summary="正在解析服务信息", created_by=admin.id, started_at=now - timedelta(seconds=8)),
            ScanTask(task_name=f"{DEMO_MARKER} 网络设备巡检", target="10.10.10.51", scan_type="port_scan", status="failed", result_summary="授权测试目标暂不可达", error_message="Demo：目标暂不可达", created_by=admin.id, started_at=now - timedelta(hours=1), finished_at=now - timedelta(minutes=59)),
        ]
        db.add_all(scans)
        db.flush()
        db.add_all([
            ScanResult(scan_task_id=scans[0].id, asset_id=assets[0].id, result_type="service", ip_address=assets[0].ip_address, port=443, protocol="tcp", service_name="https", product_name="nginx", service_version="1.24.0", raw_summary=json.dumps({"demo": True, "service": "nginx", "version": "1.24.0"}), normalized_data="10.10.10.11:443/tcp nginx 1.24.0"),
            ScanResult(scan_task_id=scans[0].id, asset_id=assets[0].id, result_type="service", ip_address=assets[0].ip_address, port=22, protocol="tcp", service_name="ssh", product_name="OpenSSH", service_version="8.9", raw_summary=json.dumps({"demo": True, "service": "OpenSSH", "version": "8.9"}), normalized_data="10.10.10.11:22/tcp OpenSSH 8.9"),
        ])

        report = SecurityReport(
            report_name=f"{DEMO_MARKER} 企业安全运营报告",
            period_start=now - timedelta(days=30), period_end=now,
            generated_at=now, asset_count=5, online_asset_count=5,
            high_risk_asset_count=3, vulnerability_count=8, cve_count=8,
            high_risk_vulnerability_count=5,
            risk_distribution=json.dumps({"critical": 2, "high": 3, "medium": 2, "low": 1}),
            scan_statistics=json.dumps({"total": 3, "completed": 1, "success_rate": 33.33}),
            vulnerability_trend=json.dumps([]),
            top_risk_assets=json.dumps([{"asset_id": assets[0].id, "ip_address": assets[0].ip_address, "hostname": assets[0].hostname, "risk_score": 100, "vulnerability_count": 2}]),
            recommendations=json.dumps(["优先核实并处置Critical候选漏洞", "完成High风险资产的版本升级与复测", "保持授权资产周期巡检"]),
            report_html="<h1>SecureOps Demo安全运营报告</h1><p>本报告仅包含明确标记的Demo测试数据。</p>",
            created_by=admin.id,
        )
        db.add(report)
        db.commit()
        print("SecureOps Demo V2 初始化完成：5个资产、8个漏洞、3个扫描任务、1份报告")
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_v2()
