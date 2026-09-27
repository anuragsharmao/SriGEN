"""SQLite database connection and session management using SQLAlchemy."""

from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# SQLite requires check_same_thread=False for multithreaded FastAPI requests
engine = create_engine(
    settings.DATABASE_URL,
    connect_args=(
        {"check_same_thread": False, "timeout": 30}
        if "sqlite" in settings.DATABASE_URL
        else {}
    ),
    **({"execution_options": {"sqlite_raw_colnames": True}} if "sqlite" in settings.DATABASE_URL else {}),
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency to yield a database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize all tables defined in models."""
    import app.db.models  # Ensure models are imported
    Base.metadata.create_all(bind=engine)

    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")
            connection.exec_driver_sql("PRAGMA busy_timeout=30000")

    # create_all() does not update existing SQLite tables when a model gains
    # a column. Keep this lightweight migration here until a full migration
    # tool is introduced.
    if engine.dialect.name == "sqlite":
        for table_name in ("security_actions", "disclosure_items"):
            columns = {column["name"] for column in inspect(engine).get_columns(table_name)}
            if "sensitivity_tier" not in columns:
                with engine.begin() as connection:
                    connection.execute(text(
                        f"ALTER TABLE {table_name} ADD COLUMN sensitivity_tier VARCHAR(20)"
                    ))
