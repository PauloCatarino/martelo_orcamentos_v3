"""Import checks for the DefMaquina model."""

from __future__ import annotations


def test_def_maquina_model_imports() -> None:
    from app.models.def_maquina import DefMaquina

    assert DefMaquina is not None


def test_def_maquina_is_registered_in_models() -> None:
    from app.models import DefMaquina

    assert DefMaquina is not None


def test_def_maquina_tablename() -> None:
    from app.models.def_maquina import DefMaquina

    assert DefMaquina.__tablename__ == "def_maquinas"


def test_def_maquina_has_expected_columns() -> None:
    from app.models.def_maquina import DefMaquina

    columns = set(DefMaquina.__table__.columns.keys())
    expected = {
        "id",
        "codigo",
        "nome",
        "descricao",
        "tipo",
        "custo_hora",
        "ativo",
        "observacoes",
        "created_at",
        "updated_at",
    }
    assert expected <= columns


def test_def_maquina_codigo_unique_and_indexes() -> None:
    from app.models.def_maquina import DefMaquina

    table = DefMaquina.__table__

    unique_columns: set[str] = set()
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            unique_columns |= {column.name for column in constraint.columns}
    assert "codigo" in unique_columns

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("tipo",) in indexed_columns
    assert ("ativo",) in indexed_columns
