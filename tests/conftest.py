"""Shared pytest configuration and fixtures.

The shared ``session`` fixture hands each test a SQLAlchemy ``Session`` on a
fresh in-memory SQLite database and — crucially — **disposes the engine** on
teardown. Test modules used to inline this boilerplate but never disposed the
engine, leaking native connections that the cyclic garbage collector then
finalized at an arbitrary later moment; on Windows that occasionally fired
mid-test and aborted the whole run with a native "access violation". With every
engine now disposed deterministically (here and in the few modules that keep a
bespoke fixture), that crash no longer happens and no GC workaround is needed.

Modules can still define their own ``session`` fixture when they need something
different (it overrides this one).
"""

from __future__ import annotations

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    """Map ``BigInteger`` autoincrement PKs to SQLite's ``INTEGER``."""
    return "INTEGER"


@pytest.fixture()
def session():
    """A Session on a throwaway in-memory SQLite DB; engine disposed on teardown."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            yield db
    finally:
        engine.dispose()
