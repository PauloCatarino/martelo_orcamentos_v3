"""Import checks for the DefValuesetModeloLinha model."""

from __future__ import annotations


def test_model_imports() -> None:
    from app.models.def_valueset_modelo_linha import DefValuesetModeloLinha

    assert DefValuesetModeloLinha is not None


def test_model_is_registered_in_models() -> None:
    from app.models import DefValuesetModeloLinha

    assert DefValuesetModeloLinha is not None


def test_tablename_columns_and_foreign_keys() -> None:
    from app.models.def_valueset_modelo_linha import DefValuesetModeloLinha

    assert DefValuesetModeloLinha.__tablename__ == "def_valueset_modelo_linhas"
    table = DefValuesetModeloLinha.__table__
    columns = set(table.columns.keys())
    assert {
        "id",
        "def_valueset_modelo_id",
        "chave",
        "codigo_opcao",
        "nome_opcao",
        "padrao",
        "ordem",
        "materia_prima_id",
        "ref_materia_prima",
        "descricao_materia_prima",
        "valor_texto",
        "origem",
        "editado_localmente",
        "ativo",
        "observacoes",
        "created_at",
        "updated_at",
    } <= columns
    fk_targets = {fk.column.table.name for fk in table.foreign_keys}
    assert {"def_valueset_modelos", "def_materias_primas"} <= fk_targets


def test_unique_indexes_and_relationships() -> None:
    from app.models.def_valueset_modelo_linha import DefValuesetModeloLinha

    table = DefValuesetModeloLinha.__table__
    unique_sets = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("def_valueset_modelo_id", "chave", "codigo_opcao") in unique_sets

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("def_valueset_modelo_id",) in indexed_columns
    assert ("chave",) in indexed_columns
    assert ("materia_prima_id",) in indexed_columns
    assert ("ativo",) in indexed_columns
    assert hasattr(DefValuesetModeloLinha, "modelo")
    assert hasattr(DefValuesetModeloLinha, "materia_prima")
