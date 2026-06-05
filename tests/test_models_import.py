"""Import checks for SQLAlchemy models."""

from __future__ import annotations


def test_models_import_and_mapper_configuration() -> None:
    from sqlalchemy.orm import configure_mappers

    from app.db.base import Base
    from app.models import (
        Cliente,
        DefPeca,
        DefPecaComponente,
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
    assert DefPeca.__tablename__ == "def_pecas"
    assert DefPeca.orla_c1.property.columns[0].default.arg == 0
    assert DefPecaComponente.__tablename__ == "def_peca_componentes"
    assert Orcamento.__tablename__ == "orcamentos"
    assert OrcamentoVersao.__tablename__ == "orcamento_versoes"
    assert OrcamentoItem.__tablename__ == "orcamento_items"
    assert OrcamentoItemModulo.__tablename__ == "orcamento_item_modulos"
    assert OrcamentoItemVariavel.__tablename__ == "orcamento_item_variaveis"
    assert {
        "users",
        "clientes",
        "def_pecas",
        "def_peca_componentes",
        "orcamentos",
        "orcamento_versoes",
        "orcamento_items",
        "orcamento_item_modulos",
        "orcamento_item_variaveis",
    }.issubset(Base.metadata.tables)
