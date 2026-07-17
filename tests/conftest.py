"""Shared pytest configuration and fixtures.

Two things live here:

* A shared ``session`` fixture that hands each test a SQLAlchemy ``Session`` on a
  fresh in-memory SQLite database and — crucially — **disposes the engine** on
  teardown. Most test modules used to inline this boilerplate but never disposed
  the engine, leaking native connections. Modules can still define their own
  ``session`` fixture when they need something different (it overrides this one).

* A session-wide guard that disables the *cyclic* garbage collector. Tests that
  still create engines/Qt widgets inline (without the shared fixture) leave
  objects for the cyclic collector to finalize at an arbitrary later moment; on
  Windows that occasionally fired mid-test and aborted the whole run with a
  native "access violation". Reference-counted cleanup (the shared fixture's
  ``engine.dispose()`` included) keeps working; only the unpredictable cyclic
  pass is turned off.
"""

from __future__ import annotations

import gc

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


@pytest.fixture(autouse=True, scope="session")
def _disable_cyclic_gc_during_session():
    """Keep the cyclic GC from finalizing native objects mid-test on Windows."""
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if was_enabled:
            gc.enable()
