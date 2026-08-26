from sqlalchemy import select

from app.models import CveIntelligence, ScanResult, ScanTask, Vulnerability
from app.services.scan_result_processor import process_scan_results
from app.services.scanner import DiscoveredService


def test_scan_result_processor_creates_and_deduplicates_vulnerability():
    from conftest import SessionTesting

    with SessionTesting() as session:
        cve = CveIntelligence(
            cve_id="CVE-2025-0001",
            title="Test nginx issue",
            description="Authorized test fixture",
            affected_products="nginx 1.24",
            severity="high",
            cvss_score=8.1,
        )
        task = ScanTask(task_name="processor test", target="192.0.2.44", scan_type="port_scan", status="running")
        session.add_all([cve, task])
        session.flush()
        service = DiscoveredService("192.0.2.44", "fixture", 443, "tcp", "open", "https", "nginx", "1.24", {"name": "https", "product": "nginx", "version": "1.24"})

        first = process_scan_results(session, task, [service])
        session.commit()
        second = process_scan_results(session, task, [service])
        session.commit()

        assert first["saved_results"] == 1
        assert first["created_vulnerabilities"] == 1
        assert second["saved_results"] == 1
        assert second["created_vulnerabilities"] == 0
        assert session.scalar(select(ScanResult).where(ScanResult.scan_task_id == task.id)) is not None
        assert len(session.scalars(select(Vulnerability).where(Vulnerability.cve_id == cve.cve_id)).all()) == 1
