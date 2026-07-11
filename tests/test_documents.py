"""Tests for document endpoints."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient


class TestDocumentUpload:
    """Test document upload endpoint."""

    def test_upload_requires_auth(self, client: TestClient):
        resp = client.post("/api/v1/documents/upload")
        assert resp.status_code == 401

    def test_upload_no_file(self, client: TestClient, auth_headers):
        resp = client.post("/api/v1/documents/upload", headers=auth_headers)
        assert resp.status_code == 422

    def test_upload_unsupported_format(self, client: TestClient, auth_headers):
        resp = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
            data={"mode": "extract"},
        )
        assert resp.status_code == 400

    def test_upload_success_png(self, client: TestClient, auth_headers):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        resp = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test.png", buf, "image/png")},
            data={"mode": "extract"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["document_id"] > 0
        assert data["job_id"] > 0
        assert data["status"] == "queued"

    def test_upload_with_api_key(self, client: TestClient, api_key_headers):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="blue")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        resp = client.post(
            "/api/v1/documents/upload",
            headers=api_key_headers,
            files={"file": ("test2.png", buf, "image/png")},
            data={"mode": "describe"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "queued"

    def test_upload_ask_mode(self, client: TestClient, auth_headers):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="green")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        resp = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test3.png", buf, "image/png")},
            data={"mode": "ask", "prompt": "What is this?"},
        )
        assert resp.status_code == 201


class TestListDocuments:
    """Test listing documents."""

    def test_list_empty(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/documents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["documents"] == []

    def test_list_requires_auth(self, client: TestClient):
        resp = client.get("/api/v1/documents")
        assert resp.status_code == 401

    def test_list_after_upload(self, client: TestClient, auth_headers):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="yellow")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("list-test.png", buf, "image/png")},
            data={"mode": "extract"},
        )

        resp = client.get("/api/v1/documents", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["documents"][0]["filename"] == "list-test.png"
        assert data["documents"][0]["status"] == "queued"


class TestGetDocument:
    """Test getting a specific document."""

    def test_get_not_found(self, client: TestClient, auth_headers):
        resp = client.get("/api/v1/documents/99999", headers=auth_headers)
        assert resp.status_code == 404

    def test_get_requires_auth(self, client: TestClient):
        resp = client.get("/api/v1/documents/1")
        assert resp.status_code == 401

    def test_get_document(self, client: TestClient, auth_headers):
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        upload_resp = client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("get-test.png", buf, "image/png")},
            data={"mode": "extract"},
        )
        doc_id = upload_resp.json()["document_id"]

        resp = client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == doc_id
        assert data["filename"] == "get-test.png"
        assert data["file_format"] == "png"
        assert data["page_count"] == 1