"""Declarative SQLAlchemy base."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for future SQLAlchemy models."""


target_metadata = Base.metadata

