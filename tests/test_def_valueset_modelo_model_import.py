"""Import checks for the DefValuesetModelo model."""

from __future__ import annotations


def test_model_imports() -> None:
    from app.models.def_valueset_modelo import DefValuesetModelo

    assert DefValuesetModelo is not None


def test_model_is_registered_in_models() -> None:
    from app.models import DefValuesetModelo

    assert DefValuesetModelo is not None


def test_tablename_and_columns() -> None:
    from app.models.def_valueset_modelo import DefValuesetModelo

    assert DefValuesetModelo.__tablename__ == "def_valueset_modelos"
    columns = set(DefValuesetModelo.__table__.columns.keys())
    assert {
        "id",
        "codigo",
        "nome",
        "descricao",
        "tipo",
        "ativo",
        "observacoes",
        "created_at",
        "updated_at",
    } <= columns


def test_constraints_indexes_and_relationships() -> None:
    from app.models.def_valueset_modelo import DefValuesetModelo

    table = DefValuesetModelo.__table__
    unique_columns: set[str] = set()
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            unique_columns |= {column.name for column in constraint.columns}
    assert "codigo" in unique_columns

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("codigo",) in indexed_columns
    assert ("ativo",) in indexed_columns
    assert hasattr(DefValuesetModelo, "linhas")
