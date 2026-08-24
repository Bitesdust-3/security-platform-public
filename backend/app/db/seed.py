"""Optional, explicitly enabled demo data for local demonstrations."""

import os

from app.core.security import hash_password
from app.database import SessionLocal
from app.models import Asset, Role, User, Vulnerability


def seed_demo_data() -> None:
    if os.getenv("SEED_DEMO_DATA", "false").lower() != "true":
        return
    db = SessionLocal()
    try:
        admin_role = db.query(Role).filter(Role.name == "admin").first()
        if admin_role is None:
            admin_role = Role(name="admin", description="演示管理员")
            db.add(admin_role)
        user_role = db.query(Role).filter(Role.name == "user").first()
        if user_role is None:
            user_role = Role(name="user", description="普通用户")
            db.add(user_role)
        db.flush()
        username = os.getenv("DEMO_ADMIN_USERNAME", "admin")
        email = os.getenv("DEMO_ADMIN_EMAIL", "admin@example.com")
        password = os.getenv("DEMO_ADMIN_PASSWORD")
        if not password:
            raise RuntimeError("SEED_DEMO_DATA=true 时必须设置 DEMO_ADMIN_PASSWORD")
        admin = db.query(User).filter(User.username == username).first()
        if admin is None:
            admin = User(username=username, email=email, hashed_password=hash_password(password), roles=[admin_role])
            db.add(admin)
        if db.query(Asset).count() == 0:
            assets = [
                Asset(asset_name="demo-web-01", ip_address="192.0.2.10", hostname="demo-web-01", asset_type="server", importance=5, status="active", os_info="Linux", description="演示数据"),
                Asset(asset_name="demo-db-01", ip_address="192.0.2.20", hostname="demo-db-01", asset_type="database", importance=4, status="active", os_info="Linux", description="演示数据"),
            ]
            db.add_all(assets)
            db.flush()
            db.add_all([
                Vulnerability(title="演示严重漏洞", cve_id="CVE-2024-10001", severity="critical", cvss_score=9.8, status="open", asset_id=assets[0].id, source="demo"),
                Vulnerability(title="演示中危漏洞", cve_id="CVE-2024-10002", severity="medium", cvss_score=5.4, status="processing", asset_id=assets[1].id, source="demo"),
            ])
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
