from contextlib import asynccontextmanager
from fastapi import FastAPI
import pytest
from fastapi.testclient import TestClient
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio.session import async_sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.db.database import Base, async_get_db
from app.main import app
from app.db.schemas import UserSchema
from app.services.user_auth_service import get_current_active_user
from sqlalchemy.orm import declarative_base, sessionmaker

SQLITE_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

async_engine = create_async_engine(SQLITE_DATABASE_URL, echo=False)

TestingAsyncSessionLocal = sessionmaker(
    async_engine,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def test_lifespan(app: FastAPI):
    yield


@pytest_asyncio.fixture
async def db_session():
    connection = await async_engine.connect()
    transaction = await connection.begin()
    async_session = AsyncSession(bind=connection)

    await connection.run_sync(Base.metadata.create_all)

    yield async_session
    await async_session.close()
    await transaction.rollback()
    await connection.close()


@pytest.fixture
def mock_current_user():
    """Fixture to mock get_current_active_user"""
    return UserSchema(id=1, email="test@example.com", is_polling=False)


@pytest.fixture()
def test_client(db_session, mock_current_user):
    """Create a test client that uses the override_get_db fixture to return a session."""

    def override_get_db():
        try:
            yield db_session
        finally:
            db_session.close()

    async def mock_get_current_active_user():
        return mock_current_user

    app.dependency_overrides[async_get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = mock_get_current_active_user
    app.router.lifespan_context = test_lifespan
    with TestClient(app) as test_client:
        yield test_client
