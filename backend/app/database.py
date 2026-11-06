"""Database engine, session factory and declarative base."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite needs check_same_thread=False when used across FastAPI threads.
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Alembic is used for real migrations; this is a
    convenience for SQLite/demo and first-run bootstrapping."""
    # Import models so they register on the metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_columns()


def _ensure_columns() -> None:
    """Lightweight, idempotent column back-fill for existing SQLite databases.

    ``create_all`` never ALTERs an existing table, so new columns added to the
    ORM (e.g. Persona.birth_year / death_year) must be added by hand for demo
    databases created before the upgrade. Postgres deployments should use
    Alembic; this is a no-op-safe convenience for the local SQLite file."""
    from sqlalchemy import inspect, text

    wanted = {
        "personas": {
            "birth_year": "INTEGER",
            "death_year": "INTEGER",
            "birth_date": "VARCHAR(32) DEFAULT ''",
            "death_date": "VARCHAR(32) DEFAULT ''",
            "knowledge_cutoff": "VARCHAR(32) DEFAULT ''",
            "knowledge_cutoff_reason": "VARCHAR(255) DEFAULT ''",
        },
    }
    try:
        inspector = inspect(engine)
        existing_tables = set(inspector.get_table_names())
        with engine.begin() as conn:
            for table, cols in wanted.items():
                if table not in existing_tables:
                    continue
                present = {c["name"] for c in inspector.get_columns(table)}
                for col, ddl in cols.items():
                    if col not in present:
                        conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {col} {ddl}'))
    except Exception:  # noqa: BLE001 — never block startup on a back-fill
        pass
