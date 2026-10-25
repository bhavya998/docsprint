"""Tests for usage tracking endpoints."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from docsprint.models.usage import UsageRecord

NOW = datetime.now(timezone.utc)


class TestUsage:
    """Test usage tracking and quota endpoints."""

    def test_usage_requires_auth(self, client: TestClient):
        resp = client.get("/api/v1/usage")
        assert resp.status_code == 401

    def test_usage_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/usage", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "free"
        assert data["pages_used"] == 0
        assert data["pages_limit"] == 10
        assert "period" in data

    def test_usage_with_data(self, client: TestClient, auth_headers, test_user, db_session: Session):
        # Simulate usage record
        record = UsageRecord(
            user_id=test_user.id,
            pages_processed=7,
            month=NOW.month,
            year=NOW.year,
        )
        db_session.add(record)
        db_session.commit()

        resp = client.get("/api/v1/usage", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["pages_used"] == 7

    def test_usage_history_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/usage/history", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["records"] == []

    def test_usage_history_with_data(
        self, client: TestClient, auth_headers, test_user, db_session: Session
    ):
        record = UsageRecord(
            user_id=test_user.id,
            pages_processed=5,
            month=6,
            year=2026,
        )
        db_session.add(record)
        db_session.commit()

        resp = client.get("/api/v1/usage/history", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["records"][0]["pages_processed"] == 5
        assert data["records"][0]["month"] == 6

    def test_quota_enforcement(self, client: TestClient, auth_headers, test_user, db_session: Session):
        """Test that a user at quota limit cannot upload more files."""
        # Fill up the free tier quota
        record = UsageRecord(
            user_id=test_user.id,
            pages_processed=10,  # exactly at the free tier limit
            month=NOW.month,
            year=NOW.year,
        )
        db_session.add(record)
        db_session.commit()

        from PIL import Image
        import io

        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        resp = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("quota-test.png", buf, "image/png")},
            data={"mode": "extract"},
        )
        assert resp.status_code == 429