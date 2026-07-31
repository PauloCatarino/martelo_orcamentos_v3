"""SQLAlchemy engine factory."""

from __future__ import annotations

from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from app.config.settings import settings


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    """Engine com as credenciais do ``.env`` — scripts de seed e alembic.

    A aplicacao nao usa este: as credenciais dela vem do login, por
    ``criar_engine``.
    """
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


def criar_engine(user: str, password: str) -> Engine:
    """Engine para as credenciais de uma pessoa concreta.

    Cada utilizador do Martelo tem a sua conta MySQL, por isso ha' um engine
    por sessao — nao se guarda em cache nem se partilha, ao contrario do
    ``get_engine``.
    """
    return create_engine(
        settings.database_url_para(user, password),
        pool_pre_ping=True,
        future=True,
    )
