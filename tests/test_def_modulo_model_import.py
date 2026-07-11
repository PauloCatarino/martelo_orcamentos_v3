"""Import checks for the module library models (phase 8U.0)."""

from __future__ import annotations


def test_def_modulo_models_registered() -> None:
    from sqlalchemy.orm import configure_mappers

    from app.db.base import Base
    from app.models import DefModulo, DefModuloLinha

    configure_mappers()

    assert DefModulo.__tablename__ == "def_modulos"
    assert DefModuloLinha.__tablename__ == "def_modulo_linhas"
    assert "def_modulos" in Base.metadata.tables
    assert "def_modulo_linhas" in Base.metadata.tables


def test_def_modulo_linha_has_no_material_snapshot() -> None:
    # Modules store ONLY the parametric structure: never material/price/orla-cost
    # or real-dimension snapshot columns.
    from app.db.base import Base

    colunas = set(Base.metadata.tables["def_modulo_linhas"].columns.keys())

    # Structure columns present.
    for esperado in (
        "tipo_linha",
        "qt_mod",
        "qt_und",
        "comp",
        "larg",
        "esp",
        "chave_valueset",
        "prioridade_valueset",
        "codigo_orlas",
        "def_regra_quantidade_id",
        "linha_pai_ordem",
        "nivel",
    ):
        assert esperado in colunas

    # No material/price/real-dimension snapshot.
    for proibido in (
        "preco_liquido",
        "ref_le",
        "mat_default",
        "comp_real",
        "larg_real",
        "custo_mp",
        "custo_orlas",
        "materia_prima_id",
    ):
        assert proibido not in colunas


def test_def_modulo_linha_cascade_fk() -> None:
    from app.db.base import Base

    coluna = Base.metadata.tables["def_modulo_linhas"].columns["def_modulo_id"]
    fks = list(coluna.foreign_keys)
    assert any(fk.column.table.name == "def_modulos" for fk in fks)
    assert any(fk.ondelete == "CASCADE" for fk in fks)
