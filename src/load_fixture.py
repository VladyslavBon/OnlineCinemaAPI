from sqlalchemy.orm import Session
from database.fixtures import load_fixtures
from database.session_postgresql import PostgresqlSessionLocal
from database.session_sqlite import SqliteSessionLocal


def init_db():
    db: Session = PostgresqlSessionLocal()  # If SQLite db use SqliteSessionLocal() here
    try:
        load_fixtures(db)
        print("Database seeding completed successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
