import json
from datetime import datetime, timezone

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models import CveIntelligence
from app.services import cve_sync


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _payload(description: str, score: float) -> dict:
    return {
        "vulnerabilities": [{
            "cve": {
                "id": "CVE-2024-12345",
                "descriptions": [{"lang": "en", "value": description}],
                "metrics": {"cvssMetricV31": [{"cvssData": {"baseScore": score, "baseSeverity": "HIGH"}}]},
                "published": "2024-01-01T00:00:00.000Z",
                "lastModified": "2024-01-02T00:00:00.000Z",
                "references": [{"url": "https://example.test/advisory"}],
                "configurations": [],
            }
        }]
    }


def test_nvd_sync_fixture_is_idempotent(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    monkeypatch.setattr(cve_sync.requests, "get", lambda *args, **kwargs: FakeResponse(_payload("Initial description", 7.5)))

    with Session(engine) as db:
        assert cve_sync.sync_nvd(db, datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 3, tzinfo=timezone.utc)) == (1, 0)
        record = db.scalar(select(CveIntelligence).where(CveIntelligence.cve_id == "CVE-2024-12345"))
        assert record is not None
        assert record.severity == "high"
        assert json.loads(record.references)[0].startswith("https://")

    monkeypatch.setattr(cve_sync.requests, "get", lambda *args, **kwargs: FakeResponse(_payload("Updated description", 9.1)))
    with Session(engine) as db:
        assert cve_sync.sync_nvd(db, datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 1, 3, tzinfo=timezone.utc)) == (1, 1)
        rows = list(db.scalars(select(CveIntelligence)).all())
        assert len(rows) == 1
        assert rows[0].description == "Updated description"
        assert rows[0].severity == "high"
