"""Import checks for the DefPecaComponente model."""

from __future__ import annotations


def test_def_peca_componente_model_imports() -> None:
    from sqlalchemy.orm import configure_mappers

    from app.db.base import Base
    from app.models import DefPecaComponente

    configure_mappers()

    assert DefPecaComponente.__tablename__ == "def_peca_componentes"
    assert "def_peca_componentes" in Base.metadata.tables
    assert DefPecaComponente.tipo_componente.property.columns[0].default.arg == "PECA"
    # Phase 8T.5.1: optional FK to a configurable quantity rule.
    tabela = Base.metadata.tables["def_peca_componentes"]
    assert "def_regra_quantidade_id" in tabela.columns
    coluna = tabela.columns["def_regra_quantidade_id"]
    assert coluna.nullable is True
    assert any(
        fk.column.table.name == "def_regras_quantidade" for fk in coluna.foreign_keys
    )
