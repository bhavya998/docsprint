"""Full API integration tests — health check, auth flow, document lifecycle."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


class TestHealth:
    """Health check endpoint."""

    def test_health(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "version" in data


class TestOpenApi:
    """OpenAPI schema endpoint."""

    def test_openapi_schema(self, client: TestClient):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "paths" in data
        assert "/api/v1/auth/register" in data["paths"]
        assert "/api/v1/auth/login" in data["paths"]
        assert "/api/v1/documents/upload" in data["paths"]


class TestFullFlow:
    """Test complete user flow from registration to document viewing."""

    def test_full_flow(self, client: TestClient):
        # 1. Register
        resp = client.post(
            "/api/v1/auth/register",
            json={"email": "flow@example.com", "password": "password123"},
        )
        assert resp.status_code == 201
        token = resp.json()["access_token"]
        api_key = resp.json()["user"]["api_key"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Check /me
        me = client.get("/api/v1/auth/me", headers=headers)
        assert me.status_code == 200
        assert me.json()["email"] == "flow@example.com"

        # 3. Check usage is empty
        usage = client.get("/api/v1/usage", headers=headers)
        assert usage.status_code == 200
        assert usage.json()["pages_used"] == 0

        # 4. Upload a document
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="purple")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        upload = client.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("flow-test.png", buf, "image/png")},
            data={"mode": "extract"},
        )
        assert upload.status_code == 201
        doc_id = upload.json()["document_id"]
        job_id = upload.json()["job_id"]

        # 5. List documents
        docs = client.get("/api/v1/documents", headers=headers)
        assert docs.status_code == 200
        assert docs.json()["total"] == 1

        # 6. Get document detail
        doc = client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert doc.status_code == 200
        assert doc.json()["status"] == "queued"

        # 7. Get job status
        job = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
        assert job.status_code == 200
        assert job.json()["status"] == "queued"

        # 8. Get document result (no result yet)
        result = client.get(f"/api/v1/documents/{doc_id}/result", headers=headers)
        assert result.status_code == 200

        # 9. API key access
        api_headers = {"X-API-Key": api_key}
        api_me = client.get("/api/v1/auth/me", headers=api_headers)
        assert api_me.status_code == 200
        assert api_me.json()["email"] == "flow@example.com"