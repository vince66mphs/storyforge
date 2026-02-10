"""Root test configuration — DB engine, test client, env override."""

import os

# Override DATABASE_URL BEFORE any app imports so the lru_cached Settings
# points at the test database.
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://vince:password@localhost:5432/storyforge_test"
)
os.environ.setdefault("MOA_ENABLED", "true")
os.environ.setdefault("WORKFLOW_DIR", "/home/vince/storyforge/workflows")
os.environ.setdefault("STATIC_DIR", "/tmp/storyforge_test_static")

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.database import Base, get_session
from app.main import app


# ── Database fixtures ─────────────────────────────────────────────────

TEST_DB_URL_ASYNC = "postgresql+asyncpg://vince:password@localhost:5432/storyforge_test"
TEST_DB_URL_SYNC = "postgresql+psycopg2://vince:password@localhost:5432/storyforge_test"


def pytest_sessionstart(session):
    """Create tables synchronously before any tests run (no event loop needed)."""
    engine = create_engine(TEST_DB_URL_SYNC, echo=False)
    Base.metadata.create_all(engine)
    engine.dispose()


def pytest_sessionfinish(session, exitstatus):
    """Drop tables synchronously after all tests complete."""
    engine = create_engine(TEST_DB_URL_SYNC, echo=False)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS world_bible CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS nodes CASCADE"))
        conn.execute(text("DROP TABLE IF EXISTS stories CASCADE"))
    engine.dispose()


@pytest.fixture
async def db_session():
    """Provide a transactional database session that rolls back after each test.

    Creates a fresh engine per test to avoid event loop contamination.
    """
    engine = create_async_engine(TEST_DB_URL_ASYNC, echo=False, pool_size=2)
    async with engine.connect() as conn:
        trans = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
    await engine.dispose()


# ── FastAPI test client ───────────────────────────────────────────────

@pytest.fixture
async def client(db_session: AsyncSession):
    """AsyncClient wired to the test database session."""

    async def _override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = _override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
