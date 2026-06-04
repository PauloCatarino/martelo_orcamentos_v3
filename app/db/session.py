"""Database session helpers."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.db.database import get_engine


SessionLocal = sessionmaker(
    bind=get_engine(),
    autocommit=False,
    autoflush=False,
    future=True,
)


def get_session() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and close it afterwards."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

