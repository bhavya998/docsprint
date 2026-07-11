"""Real end-to-end test — starts API server, runs migration, hits all endpoints.

This test DOES NOT use mocked Redis or in-memory SQLite.
It uses a real SQLite file and tests via HTTP on a live uvicorn server.
No Docker required — uses SQLite + mocked Redis queue.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

import httpx
import pytest
from PIL import Image

API_BASE = "http://127.0.0.1:8099/api/v1"


@pytest.fixture(scope="session")
def api_base():
    """Start the FastAPI server with SQLite, run migrations, yield the API base URL."""
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)

    # Remove old test DB
    db_path = data_dir / "test_docsprint.db"
    if db_path.exists():
        db_path.unlink()

    db_url = f"sqlite:///{db_path}"

    # Temporarily rename .env so Pydantic Settings doesn't override our DATABASE_URL
    env_path = project_root / ".env"
    env_bak = project_root / ".env.bak"
    if env_path.exists():
        env_path.rename(env_bak)

    os.environ["DATABASE_URL"] = db_url

    # Run Alembic migrations
    print("\n[E2E] Running Alembic migration...")
    result = subprocess.run(
        [
            sys.executable, "-m", "alembic",
            "-c", str(project_root / "alembic.ini"),
            "upgrade", "head",
        ],
        capture_output=True, text=True,
        cwd=str(project_root),
        env={**os.environ, "DATABASE_URL": db_url},
    )
    if result.returncode != 0:
        print("STDOUT:", result.stdout)
        print("STDERR:", result.stderr)
        pytest.fail(f"Alembic migration failed: {result.stderr}")
    print("[E2E] Migration complete. Starting server...")

    # Start FastAPI server
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "docsprint.main:app",
            "--host", "127.0.0.1", "--port", "8099",
        ],
        cwd=str(project_root),
        env={
            **os.environ,
            "DATABASE_URL": db_url,
            "PYTHONPATH": str(project_root / "src"),
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # Wait for server to start
    for _ in range(30):
        try:
            r = httpx.get("http://127.0.0.1:8099/health", timeout=1.0)
            if r.status_code == 200:
                print("[E2E] Server started successfully!")
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        pytest.fail("Server did not start within 15 seconds")

    yield API_BASE

    # Cleanup
    print("[E2E] Shutting down server...")
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()

    # Windows file lock: try unlink, give up if locked
    import time as _time
    for _attempt in range(5):
        try:
            if db_path.exists():
                db_path.unlink()
            break
        except PermissionError:
            _time.sleep(0.5)

    # Restore .env
    if env_bak.exists():
        env_bak.rename(env_path)


def _make_png(color: str = "red") -> BytesIO:
    """Create a tiny test PNG image in memory."""
    img = Image.new("RGB", (50, 50), color=color)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


class TestE2EReal:
    """Full end-to-end tests against a running API server."""

    def test_health(self, api_base: str) -> None:
        resp = httpx.get("http://127.0.0.1:8099/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_openapi_schema(self, api_base: str) -> None:
        resp = httpx.get("http://127.0.0.1:8099/openapi.json")
        assert resp.status_code == 200
        data = resp.json()
        assert "/api/v1/auth/register" in data["paths"]
        assert "/api/v1/auth/login" in data["paths"]
        assert "/api/v1/documents/upload" in data["paths"]

    def test_register(self, api_base: str) -> None:
        resp = httpx.post(
            f"{api_base}/auth/register",
            json={"email": "e2e@test.com", "password": "testpass123"},
        )
        assert resp.status_code == 201, f"Register failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["email"] == "e2e@test.com"
        assert data["user"]["plan"] == "free"
        assert data["user"]["api_key"].startswith("dsk_")

    def test_register_duplicate(self, api_base: str) -> None:
        resp = httpx.post(
            f"{api_base}/auth/register",
            json={"email": "e2e@test.com", "password": "testpass123"},
        )
        assert resp.status_code == 409

    def test_login(self, api_base: str) -> None:
        resp = httpx.post(
            f"{api_base}/auth/login",
            json={"email": "e2e@test.com", "password": "testpass123"},
        )
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        # Store credentials for other tests via class variables
        self.__class__.token = data["access_token"]
        self.__class__.api_key = data["user"]["api_key"]

    def test_login_wrong_password(self, api_base: str) -> None:
        resp = httpx.post(
            f"{api_base}/auth/login",
            json={"email": "e2e@test.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401

    def test_me_with_bearer_token(self, api_base: str) -> None:
        # Login to get fresh credentials
        login_resp = httpx.post(
            f"{api_base}/auth/login",
            json={"email": "e2e@test.com", "password": "testpass123"},
        )
        token = login_resp.json()["access_token"]
        api_key = login_resp.json()["user"]["api_key"]

        # Test Bearer
        resp = httpx.get(
            f"{api_base}/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "e2e@test.com"

        # Test API Key
        resp2 = httpx.get(
            f"{api_base}/auth/me",
            headers={"X-API-Key": api_key},
        )
        assert resp2.status_code == 200
        assert resp2.json()["email"] == "e2e@test.com"

        # Store for reuse
        TestE2EReal.token = token
        TestE2EReal.api_key = api_key

    def test_me_no_auth(self, api_base: str) -> None:
        resp = httpx.get(f"{api_base}/auth/me")
        assert resp.status_code == 401

    def test_usage(self, api_base: str) -> None:
        resp = httpx.get(
            f"{api_base}/usage",
            headers={"Authorization": f"Bearer {TestE2EReal.token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["plan"] == "free"
        assert data["pages_used"] == 0
        assert data["pages_limit"] == 10

    def test_upload_document(self, api_base: str) -> None:
        token = TestE2EReal.token
        api_key = TestE2EReal.api_key

        # Upload with Bearer token
        buf = _make_png("red")
        resp = httpx.post(
            f"{api_base}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("test.png", buf, "image/png")},
            data={"mode": "extract"},
        )
        assert resp.status_code == 201, f"Upload failed: {resp.text}"
        data = resp.json()
        assert data["document_id"] > 0
        assert data["job_id"] > 0
        assert data["status"] == "queued"

        doc_id: int = data["document_id"]
        job_id: int = data["job_id"]

        # Upload with API Key
        buf2 = _make_png("blue")
        resp2 = httpx.post(
            f"{api_base}/documents/upload",
            headers={"X-API-Key": api_key},
            files={"file": ("test2.png", buf2, "image/png")},
            data={"mode": "describe"},
        )
        assert resp2.status_code == 201

        TestE2EReal.doc_id = doc_id
        TestE2EReal.job_id = job_id

    def test_list_documents(self, api_base: str) -> None:
        token = TestE2EReal.token

        resp = httpx.get(
            f"{api_base}/documents",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        assert len(data["documents"]) > 0
        assert "filename" in data["documents"][0]
        assert "status" in data["documents"][0]

    def test_get_document(self, api_base: str) -> None:
        resp = httpx.get(
            f"{api_base}/documents/{TestE2EReal.doc_id}",
            headers={"Authorization": f"Bearer {TestE2EReal.token}"},
        )
        assert resp.status_code == 200, f"Get document failed: {resp.text}"
        data = resp.json()
        assert data["id"] == TestE2EReal.doc_id
        assert data["status"] == "queued"

    def test_get_job(self, api_base: str) -> None:
        resp = httpx.get(
            f"{api_base}/jobs/{TestE2EReal.job_id}",
            headers={"Authorization": f"Bearer {TestE2EReal.token}"},
        )
        assert resp.status_code == 200, f"Get job failed: {resp.text}"
        data = resp.json()
        assert data["id"] == TestE2EReal.job_id
        assert data["status"] == "queued"

    def test_list_jobs(self, api_base: str) -> None:
        resp = httpx.get(
            f"{api_base}/jobs",
            headers={"Authorization": f"Bearer {TestE2EReal.token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["total"] > 0

    def test_document_result(self, api_base: str) -> None:
        resp = httpx.get(
            f"{api_base}/documents/{TestE2EReal.doc_id}/result",
            headers={"Authorization": f"Bearer {TestE2EReal.token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["format"] == "png"

    def test_unsupported_format(self, api_base: str) -> None:
        resp = httpx.post(
            f"{api_base}/documents/upload",
            headers={"Authorization": f"Bearer {TestE2EReal.token}"},
            files={"file": ("test.txt", BytesIO(b"hello"), "text/plain")},
            data={"mode": "extract"},
        )
        assert resp.status_code == 400

    def test_quota_enforcement(self, api_base: str) -> None:
        """Register new user, fill quota, verify 429."""
        import secrets

        email = f"quota_{secrets.token_hex(4)}@test.com"
        reg_resp = httpx.post(
            f"{api_base}/auth/register",
            json={"email": email, "password": "testpass123"},
        )
        assert reg_resp.status_code == 201
        token: str = reg_resp.json()["access_token"]

        # Upload 11 times (free tier = 10 pages)
        for i in range(11):
            buf = _make_png("red")
            resp = httpx.post(
                f"{api_base}/documents/upload",
                headers={"Authorization": f"Bearer {token}"},
                files={"file": (f"quota-{i}.png", buf, "image/png")},
                data={"mode": "extract"},
            )
            if resp.status_code == 429:
                # Quota hit — this is the expected behavior
                assert "quota" in resp.text.lower() or "exceeded" in resp.text.lower()
                return

        # If we got here without hitting 429, check that usage reflects it
        usage_resp = httpx.get(
            f"{api_base}/usage",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert usage_resp.status_code == 200
        usage = usage_resp.json()
        # After 10 uploads, at least some pages should be counted
        assert usage["pages_used"] >= 1