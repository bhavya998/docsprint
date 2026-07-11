"""Standalone full end-to-end test — no test framework needed.

Starts server, runs migration, hits every endpoint, prints results.
Run: uv run python tests/run_full_e2e.py
"""
from __future__ import annotations

import os
import secrets
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path

import httpx
from PIL import Image

GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"
PASS = f"{GREEN}PASS{RESET}"
FAIL = f"{RED}FAIL{RESET}"
STEP = 0


def step(name: str) -> None:
    global STEP
    STEP += 1
    print(f"\n{BOLD}{CYAN}[Step {STEP}]{RESET} {name}")


def check(condition: bool, label: str) -> None:
    if condition:
        print(f"  {PASS} {label}")
    else:
        print(f"  {FAIL} {label}")
        sys.exit(1)


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    data_dir = project_root / "data" / "fulle2e"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir / "docsprint.db"
    if db_path.exists():
        db_path.unlink()
    db_url = f"sqlite:///{db_path}"

    # Backup .env
    env_path = project_root / ".env"
    env_bak = project_root / ".env.bak.fulle2e"
    if env_path.exists():
        env_path.rename(env_bak)

    # ── 1. Alembic migration ──
    step("Alembic migration")
    r = subprocess.run(
        [
            sys.executable, "-m", "alembic",
            "-c", str(project_root / "alembic.ini"),
            "upgrade", "head",
        ],
        capture_output=True, text=True,
        env={**os.environ, "DATABASE_URL": db_url},
    )
    check(r.returncode == 0, f"Migration OK: {r.stdout.strip().splitlines()[-1] if r.stdout else 'ok'}")

    # ── 2. Start server ──
    step("Start FastAPI server")
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "uvicorn", "docsprint.main:app",
            "--host", "127.0.0.1", "--port", "8099",
        ],
        env={
            **os.environ,
            "DATABASE_URL": db_url,
            "PYTHONPATH": str(project_root / "src"),
        },
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            if httpx.get("http://127.0.0.1:8099/health", timeout=1.0).status_code == 200:
                break
        except Exception:
            time.sleep(0.3)
    else:
        check(False, "Server failed to start")
    print(f"  {PASS} Server live at :8099")

    API = "http://127.0.0.1:8099/api/v1"

    # ── 3. Health ──
    step("Health check")
    r = httpx.get("http://127.0.0.1:8099/health")
    check(r.status_code == 200 and r.json()["status"] == "ok", "GET /health -> 200 ok")

    # ── 4. OpenAPI ──
    step("OpenAPI schema")
    r = httpx.get("http://127.0.0.1:8099/openapi.json")
    check(r.status_code == 200, f"GET /openapi.json -> 200 ({len(r.text)} bytes)")
    paths = r.json()["paths"]
    check("/api/v1/auth/register" in paths, "register route")
    check("/api/v1/auth/login" in paths, "login route")
    check("/api/v1/documents/upload" in paths, "upload route")
    check("/api/v1/usage" in paths, "usage route")

    # ── 5. Register ──
    step("Register new user")
    email = f"finale2e_{secrets.token_hex(4)}@docsprint.dev"
    r = httpx.post(
        f"{API}/auth/register",
        json={"email": email, "password": "testpass123"},
    )
    check(r.status_code == 201, f"POST /auth/register -> {r.status_code}")
    data = r.json()
    token = data["access_token"]
    api_key = data["user"]["api_key"]
    check(data["token_type"] == "bearer", f'token_type: {data["token_type"]}')
    check(data["user"]["email"] == email, f'email: {data["user"]["email"]}')
    check(data["user"]["plan"] == "free", "plan: free")
    check(api_key.startswith("dsk_"), f"api_key: {api_key[:15]}...")

    # ── 6. Duplicate register ──
    step("Register duplicate -> 409")
    r = httpx.post(f"{API}/auth/register", json={"email": email, "password": "testpass456"})
    check(r.status_code == 409, f"duplicate -> {r.status_code}")

    # ── 7. Login ──
    step("Login")
    r = httpx.post(f"{API}/auth/login", json={"email": email, "password": "testpass123"})
    check(r.status_code == 200, f"POST /auth/login -> {r.status_code}")
    token = r.json()["access_token"]

    # ── 8. Login wrong password ──
    step("Login wrong password -> 401")
    r = httpx.post(f"{API}/auth/login", json={"email": email, "password": "WRONG"})
    check(r.status_code == 401, f"wrong password -> {r.status_code}")

    # ── 9. /auth/me with Bearer ──
    step("GET /auth/me with Bearer token")
    r = httpx.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"})
    check(r.status_code == 200, f"me-bearer -> {r.status_code}")
    check(r.json()["email"] == email, "email matches")
    check("api_key" in r.json(), "api_key present")

    # ── 10. /auth/me with X-API-Key ──
    step("GET /auth/me with X-API-Key header")
    r = httpx.get(f"{API}/auth/me", headers={"X-API-Key": api_key})
    check(r.status_code == 200, f"me-apikey -> {r.status_code}")
    check(r.json()["email"] == email, "email matches via API key")

    # ── 11. /auth/me no auth ──
    step("GET /auth/me without auth -> 401")
    r = httpx.get(f"{API}/auth/me")
    check(r.status_code == 401, f"no-auth -> {r.status_code}")

    # ── 12. Usage initial ──
    step("GET /usage (initial — 0 pages)")
    r = httpx.get(f"{API}/usage", headers={"Authorization": f"Bearer {token}"})
    check(r.status_code == 200, f"usage -> {r.status_code}")
    u = r.json()
    check(u["plan"] == "free" and u["pages_used"] == 0 and u["pages_limit"] == 10,
          f"plan={u['plan']}, used={u['pages_used']}, limit={u['pages_limit']}")

    # ── 13. Upload extract ──
    step("POST /documents/upload (extract mode, Bearer)")
    img = Image.new("RGB", (50, 50), "red")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    r = httpx.post(
        f"{API}/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("invoice.pdf.png", buf, "image/png")},
        data={"mode": "extract"},
    )
    check(r.status_code == 201, f"upload -> {r.status_code}")
    up = r.json()
    doc_id = up["document_id"]
    job_id = up["job_id"]
    check(doc_id > 0, f"document_id={doc_id}")
    check(job_id > 0, f"job_id={job_id}")
    check(up["status"] == "queued", "status=queued")

    # ── 14. Upload with API key ──
    step("POST /documents/upload (describe mode, X-API-Key)")
    buf2 = BytesIO()
    img.save(buf2, format="PNG")
    buf2.seek(0)
    r = httpx.post(
        f"{API}/documents/upload",
        headers={"X-API-Key": api_key},
        files={"file": ("photo.png", buf2, "image/png")},
        data={"mode": "describe"},
    )
    check(r.status_code == 201, f"upload-via-apikey -> {r.status_code}")

    # ── 15. Upload ask mode ──
    step("POST /documents/upload (ask mode with prompt)")
    buf3 = BytesIO()
    img.save(buf3, format="PNG")
    buf3.seek(0)
    r = httpx.post(
        f"{API}/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("form.png", buf3, "image/png")},
        data={"mode": "ask", "prompt": "What is in this image?"},
    )
    check(r.status_code == 201, f"upload-ask -> {r.status_code}")

    # ── 16. Unsupported format ──
    step("POST /documents/upload (unsupported format -> 400)")
    r = httpx.post(
        f"{API}/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("bad.txt", BytesIO(b"nope"), "text/plain")},
        data={"mode": "extract"},
    )
    check(r.status_code == 400, f"bad format -> {r.status_code}")

    # ── 17. List documents ──
    step("GET /documents (list all)")
    r = httpx.get(f"{API}/documents", headers={"Authorization": f"Bearer {token}"})
    check(r.status_code == 200, f"list -> {r.status_code}")
    docs = r.json()
    check(docs["total"] == 3, f"total={docs['total']}")
    for d in docs["documents"]:
        print(f"  {PASS} {d['filename']} ({d['file_format']}) status={d['status']}")

    # ── 18. Get single document ──
    step("GET /documents/{id}")
    r = httpx.get(f"{API}/documents/{doc_id}", headers={"Authorization": f"Bearer {token}"})
    check(r.status_code == 200, f"get doc -> {r.status_code}")
    d = r.json()
    check(d["id"] == doc_id, "id matches")
    check(d["filename"] == "invoice.pdf.png", "filename matches")
    check(d["status"] == "queued", "status=queued")

    # ── 19. Get document result ──
    step("GET /documents/{id}/result")
    r = httpx.get(f"{API}/documents/{doc_id}/result", headers={"Authorization": f"Bearer {token}"})
    check(r.status_code == 200, f"result -> {r.status_code}")
    res = r.json()
    check(res["format"] == "png", f"format={res['format']}")
    print(f"  {PASS} pages in result: {len(res['pages'])}")

    # ── 20. Get job status ──
    step("GET /jobs/{id}")
    r = httpx.get(f"{API}/jobs/{job_id}", headers={"Authorization": f"Bearer {token}"})
    check(r.status_code == 200, f"job -> {r.status_code}")
    j = r.json()
    check(j["id"] == job_id, "job_id matches")
    check(j["status"] == "queued", "status=queued")

    # ── 21. List jobs ──
    step("GET /jobs (list)")
    r = httpx.get(f"{API}/jobs", headers={"Authorization": f"Bearer {token}"})
    check(r.status_code == 200, f"jobs list -> {r.status_code}")
    check(r.json()["total"] == 3, f"total={r.json()['total']}")

    # ── 22. Usage after uploads ──
    step("GET /usage (after 3 uploads)")
    r = httpx.get(f"{API}/usage", headers={"Authorization": f"Bearer {token}"})
    check(r.status_code == 200, "usage OK")
    u = r.json()
    check(u["pages_used"] == 3, f"pages_used={u['pages_used']} (expected 3)")
    print(f"  {PASS} usage meter: {u['pages_used']}/{u['pages_limit']} ({u['plan']})")

    # ── 23. Usage history ──
    step("GET /usage/history")
    r = httpx.get(f"{API}/usage/history", headers={"Authorization": f"Bearer {token}"})
    check(r.status_code == 200, "history OK")
    check(r.json()["total"] == 1, f"records={r.json()['total']}")

    # ── 24. Quota enforcement ──
    step("Quota enforcement: upload 8 more (limit=10, already at 3)")
    quota_hit = False
    for i in range(8):
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        r = httpx.post(
            f"{API}/documents/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (f"quota-{i}.png", buf, "image/png")},
            data={"mode": "extract"},
        )
        if r.status_code == 429:
            quota_hit = True
            print(f"  {PASS} Quota HIT at upload #{4 + i} with 429")
            check("quota" in r.text.lower() or "exceeded" in r.text.lower(),
                  "error mentions quota/exceeded")
            break
    if not quota_hit:
        r = httpx.get(f"{API}/usage", headers={"Authorization": f"Bearer {token}"})
        u = r.json()
        check(u["pages_used"] <= 10, f"pages_used={u['pages_used']} <= 10")

    # ── Cleanup ──
    step("Cleanup")
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
    for _ in range(5):
        try:
            if db_path.exists():
                db_path.unlink()
            break
        except PermissionError:
            time.sleep(0.3)
    if env_bak.exists():
        env_bak.rename(env_path)

    print(f"\n{BOLD}{GREEN}{'='*50}{RESET}")
    print(f"{BOLD}{GREEN}  ALL {STEP} STEPS PASSED — DOCSPRINT WORKS{RESET}")
    print(f"{BOLD}{GREEN}{'='*50}{RESET}")


if __name__ == "__main__":
    main()