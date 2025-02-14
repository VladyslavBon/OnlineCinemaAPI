from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config.dependencies import get_settings
from database.models.base import Base

settings = get_settings()

SQLITE_DATABASE_URL = "sqlite:///./database.db"
sqlite_engine = create_engine(SQLITE_DATABASE_URL, connect_args={"check_same_thread": False})
sqlite_connection = sqlite_engine.connect()
SqliteSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_connection)


def get_sqlite_db() -> Session:
    db = SqliteSessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_sqlite_db_contextmanager() -> Session:
    db = SqliteSessionLocal()
    try:
        yield db
    finally:
        db.close()


def reset_sqlite_database():
    with sqlite_connection.begin():
        Base.metadata.drop_all(bind=sqlite_connection)
        Base.metadata.create_all(bind=sqlite_connection)
