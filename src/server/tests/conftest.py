from contextlib import asynccontextmanager
from fastapi import FastAPI
import pytest
from httpx import AsyncClient
from httpx import ASGITransport
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.db.database import Base, async_get_db
from app.main import app
from app.services.user_auth_service import get_current_active_user
from sqlalchemy.orm import sessionmaker
from tests.fixtures.constants import USER_SCHEMA_EXAMPLE

SQLITE_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async_engine = create_async_engine(SQLITE_DATABASE_URL, echo=False, future=True)

TestingAsyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    yield


@pytest.fixture(scope="function")
async def db_session():
    connection = await async_engine.connect()
    transaction = await connection.begin()
    async_session = AsyncSession(bind=connection)

    await connection.run_sync(Base.metadata.create_all)

    yield async_session
    await async_session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture(scope="function")
def mock_current_user():
    """Fixture to mock get_current_active_user"""
    return USER_SCHEMA_EXAMPLE


@pytest.fixture(scope="function")
async def test_client(db_session, mock_current_user):
    """Create a test client that uses the override_get_db fixture to return a session."""

    async def override_get_db():
        try:
            yield db_session
        finally:
            await db_session.close()

    async def mock_get_current_active_user():
        return mock_current_user

    app.dependency_overrides[async_get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.router.lifespan_context = test_lifespan
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="https://test"
    ) as test_client:
        yield test_client
