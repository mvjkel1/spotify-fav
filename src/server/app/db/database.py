import os
from dotenv import dotenv_values, find_dotenv
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine

env_path = find_dotenv()
config = dotenv_values(env_path)

if "PROD" in dict(os.environ).keys() and dict(os.environ)["PROD"] == "RAILWAY":
    config = dict(os.environ)

SQLALCHEMY_DATABASE_URL = config.get("SQLALCHEMY_DATABASE_URL", "sqlite+aiosqlite:///:memory:")

async_engine = create_async_engine(SQLALCHEMY_DATABASE_URL, echo=False, future=True)


local_session = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def async_get_db():
    async_session = local_session()
    async with async_session as db:
        yield db
