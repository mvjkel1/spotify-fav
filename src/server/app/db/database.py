import os
from dotenv import dotenv_values, find_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

env_path = find_dotenv()
config = dotenv_values(env_path)

if "PROD" in dict(os.environ).keys() and dict(os.environ)["PROD"] == "RAILWAY":
    config = dict(os.environ)

SQLALCHEMY_DATABASE_URL = config["SQLALCHEMY_DATABASE_URL"]
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """
    Provides a database session to be used in FastAPI dependency injection. The session is
    automatically closed after the request is completed.

    Yields:
        Session: A database session to interact with the database.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
