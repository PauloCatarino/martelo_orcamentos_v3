"""Import checks for the DefValuesetChave model."""

from __future__ import annotations


def test_model_imports() -> None:
    from app.models.def_valueset_chave import DefValuesetChave

    assert DefValuesetChave is not None


def test_model_is_registered_in_models() -> None:
    from app.models import DefValuesetChave

    assert DefValuesetChave is not None


def test_tablename_and_columns() -> None:
    from app.models.def_valueset_chave import DefValuesetChave

    assert DefValuesetChave.__tablename__ == "def_valueset_chaves"
    columns = set(DefValuesetChave.__table__.columns.keys())
    assert {
        "id",
        "codigo",
        "nome",
        "descricao",
        "tipo",
        "grupo",
        "sistema",
        "ativo",
        "ordem",
        "observacoes",
        "created_at",
        "updated_at",
    } <= columns


def test_required_and_optional_columns() -> None:
    from app.models.def_valueset_chave import DefValuesetChave

    table = DefValuesetChave.__table__
    assert table.columns["codigo"].nullable is False
    assert table.columns["nome"].nullable is False
    assert table.columns["descricao"].nullable is True
    assert table.columns["tipo"].nullable is True
    assert table.columns["grupo"].nullable is True
    assert DefValuesetChave.sistema.property.columns[0].default.arg is False
    assert DefValuesetChave.ativo.property.columns[0].default.arg is True


def test_unique_and_indexes() -> None:
    from app.models.def_valueset_chave import DefValuesetChave

    table = DefValuesetChave.__table__
    unique_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("codigo",) in unique_sets

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("tipo",) in indexed_columns
    assert ("grupo",) in indexed_columns
    assert ("ativo",) in indexed_columns
