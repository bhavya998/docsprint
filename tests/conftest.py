"""Test fixtures — in-memory SQLite, test client, mock dependencies."""

from __future__ import annotations

from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from docsprint.core.dependencies import get_db
from docsprint.database import Base
from docsprint.models import Document, Job, UsageRecord, User  # noqa: F401

TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(autouse=True)
def _mock_redis(monkeypatch) -> None:
    """Prevent Redis connections in tests by mocking the queue."""

    class MockQueue:
        def enqueue(self, *a, **kw):
            pass

    monkeypatch.setattr(
        "docsprint.services.job_service.get_queue", lambda *a, **kw: MockQueue()
    )


@pytest.fixture(scope="session")
def engine():
    """Create a session-scoped in-memory SQLite engine."""
    eng = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})

    @event.listens_for(eng, "connect")
    def _pragma(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(bind=eng)

    # Override the database module globals
    import docsprint.database as db_mod

    db_mod._engine = eng
    db_mod._SyncSessionLocal = sessionmaker(
        bind=eng, autocommit=False, autoflush=False
    )

    def _test_sync_db():
        session = db_mod._SyncSessionLocal()
        try:
            yield session
        finally:
            session.close()

    monkeypatch_session = pytest.MonkeyPatch()
    monkeypatch_session.setattr(db_mod, "get_sync_db", _test_sync_db)

    yield eng
    Base.metadata.drop_all(bind=eng)
    eng.dispose()


@pytest.fixture(scope="function")
def db_session(engine) -> Generator[Session, None, None]:
    """Create a fresh database session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a FastAPI TestClient with test database session."""
    from docsprint.main import create_app

    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session: Session) -> User:
    """Create a test user and return it."""
    from docsprint.core.security import hash_password

    user = User(
        email="test@example.com",
        hashed_password=hash_password("password123"),
        plan="free",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(client: TestClient, test_user: User) -> dict:
    """Get auth headers for the test user by logging in."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password123"},
    )
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture(scope="function")
def api_key_headers(test_user: User) -> dict:
    """Get API key headers for the test user."""
    return {"X-API-Key": test_user.api_key}