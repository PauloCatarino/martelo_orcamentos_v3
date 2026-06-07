"""Import checks for the DefPeca model."""

from __future__ import annotations


def test_def_peca_model_imports() -> None:
    from sqlalchemy.orm import configure_mappers

    from app.db.base import Base
    from app.models import DefPeca

    configure_mappers()

    assert DefPeca.__tablename__ == "def_pecas"
    assert "def_pecas" in Base.metadata.tables
    assert DefPeca.tipo_peca.property.columns[0].default.arg == "SIMPLES"

    columns = DefPeca.__table__.columns
    assert {
        "chave_valueset_material",
        "permite_acabamento",
        "chave_valueset_acabamento_sup",
        "chave_valueset_acabamento_inf",
    } <= set(columns.keys())
    assert columns["chave_valueset_material"].nullable is True
    assert columns["permite_acabamento"].nullable is False
    assert DefPeca.permite_acabamento.property.columns[0].default.arg is False
