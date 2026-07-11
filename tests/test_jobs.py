"""Tests for job endpoints."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


class TestJobs:
    """Test job listing and status endpoints."""

    def test_list_jobs_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/jobs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_list_jobs_requires_auth(self, client: TestClient):
        resp = client.get("/api/v1/jobs")
        assert resp.status_code == 401

    def test_list_jobs_after_upload(self, client: TestClient, auth_headers):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("job-test.png", buf, "image/png")},
            data={"mode": "extract"},
        )

        resp = client.get("/api/v1/jobs", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["jobs"][0]["status"] == "queued"

    def test_get_job_status(self, client: TestClient, auth_headers):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        upload_resp = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("status-test.png", buf, "image/png")},
            data={"mode": "extract"},
        )
        job_id = upload_resp.json()["job_id"]

        resp = client.get(f"/api/v1/jobs/{job_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == job_id
        assert data["status"] == "queued"
        assert data["result_json"] is None

    def test_get_job_not_found(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/jobs/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_job_requires_auth(self, client: TestClient):
        resp = client.get("/api/v1/jobs/1")
        assert resp.status_code == 401


class TestDocumentResult:
    """Test the /documents/{id}/result endpoint."""

    def test_result_no_result_yet(self, client: TestClient, auth_headers):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        upload_resp = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("result-test.png", buf, "image/png")},
            data={"mode": "extract"},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = client.get(
            f"/api/v1/documents/{doc_id}/result", headers=auth_headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "png"
        assert data["pages"] == []

    def test_result_not_found(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/documents/99999/result", headers=auth_headers)
        assert resp.status_code == 404