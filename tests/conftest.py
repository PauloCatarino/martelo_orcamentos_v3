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

# O `six`/`dateutil` TÊM de ser carregados antes do PySide6, senão o gancho do
# shiboken rebenta a importar o `matplotlib.figure` com
# "'_SixMetaPathImporter' object has no attribute '_path'" -- é a mesma
# armadilha que o `deploy/rthook_dateutil.py` resolve dentro do executável e o
# `app/main.py` em desenvolvimento. Aqui é preciso porque quase todos os
# módulos de teste importam PySide6, e sem isto qualquer teste que desenhe um
# gráfico passava sozinho e falhava na suite inteira.
try:  # pragma: no cover - só ordem de importação
    import six  # noqa: F401
    import dateutil.rrule  # noqa: F401
    import dateutil.tz  # noqa: F401
except Exception:  # noqa: BLE001
    pass

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
