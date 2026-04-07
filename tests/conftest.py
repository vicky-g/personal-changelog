"""
Test fixtures.

Uses an in-memory SQLite database (via aiosqlite) so tests run without
a real PostgreSQL instance. The Entry.tags column uses JSON, which works
on both SQLite and PostgreSQL.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base


@pytest.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as s:
        yield s

    await engine.dispose()


@pytest.fixture
async def client(session: AsyncSession) -> AsyncClient:
    """
    HTTP test client wired to the FastAPI app.

    Overrides the get_session dependency so every request in a test shares
    the same in-memory SQLite session — data created in one request is
    visible to the next without a real commit.
    """
    from app.api.deps import get_session
    from app.main import app

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
