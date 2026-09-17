"""Shared pytest fixtures — isolated per-test DB via transaction rollback."""
import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "backend" / "app"))
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg2://buyorwait:buyorwait@localhost:5432/buyorwait_test",
)

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture(scope="session")
def engine():
    settings = get_settings()
    admin_url = settings.database_url.rsplit("/", 1)[0] + "/postgres"
    admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.exec_driver_sql(
            "SELECT 1 FROM pg_database WHERE datname = 'buyorwait_test'"
        ).scalar()
        if not exists:
            conn.exec_driver_sql("CREATE DATABASE buyorwait_test")
    admin_engine.dispose()

    eng = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(eng)
    yield eng
    Base.metadata.drop_all(eng)
    eng.dispose()


@pytest.fixture()
def db(engine):
    """A session wrapped in an outer transaction that is rolled back per test."""
    connection = engine.connect()
    transaction = connection.begin()
    TestingSession = sessionmaker(bind=connection)
    session = TestingSession()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    """TestClient wired to the per-test session (get_db overridden)."""
    application = create_app()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    application.dependency_overrides[get_db] = override_get_db
    with TestClient(application) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    """Register a user, return auth headers + user info."""
    import uuid
    suffix = uuid.uuid4().hex[:8]
    payload = {
        "email": f"user-{suffix}@example.com",
        "password": "Sup3rSecret!",
        "full_name": "Test User",
    }
    resp = client.post("/api/auth/signup", json=payload)
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, payload
