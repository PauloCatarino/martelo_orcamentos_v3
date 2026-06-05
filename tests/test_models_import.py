"""Import checks for SQLAlchemy models."""

from __future__ import annotations


def test_models_import_and_mapper_configuration() -> None:
    from sqlalchemy.orm import configure_mappers

    from app.db.base import Base
    from app.models import (
        Cliente,
        Orcamento,
        OrcamentoItem,
        OrcamentoItemModulo,
        OrcamentoItemVariavel,
        OrcamentoVersao,
        User,
    )

    configure_mappers()

    assert User.__tablename__ == "users"
    assert Cliente.__tablename__ == "clientes"
    assert Orcamento.__tablename__ == "orcamentos"
    assert OrcamentoVersao.__tablename__ == "orcamento_versoes"
    assert OrcamentoItem.__tablename__ == "orcamento_items"
    assert OrcamentoItemModulo.__tablename__ == "orcamento_item_modulos"
    assert OrcamentoItemVariavel.__tablename__ == "orcamento_item_variaveis"
    assert {
        "users",
        "clientes",
        "orcamentos",
        "orcamento_versoes",
        "orcamento_items",
        "orcamento_item_modulos",
        "orcamento_item_variaveis",
    }.issubset(Base.metadata.tables)
