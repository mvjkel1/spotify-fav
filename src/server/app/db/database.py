from dotenv import dotenv_values, find_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

env_path = find_dotenv()
config = dotenv_values(env_path)

SQLALCHEMY_DATABASE_URL = config.get("SQLALCHEMY_DATABASE_URL", "sqlite:///:memory:")

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
