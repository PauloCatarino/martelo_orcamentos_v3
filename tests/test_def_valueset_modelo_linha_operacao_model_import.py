"""Import checks for DefValuesetModeloLinhaOperacao model."""

from __future__ import annotations


def test_model_imports() -> None:
    from app.models.def_valueset_modelo_linha_operacao import (
        DefValuesetModeloLinhaOperacao,
    )

    assert DefValuesetModeloLinhaOperacao is not None


def test_model_is_registered_in_models() -> None:
    from app.models import DefValuesetModeloLinhaOperacao

    assert DefValuesetModeloLinhaOperacao is not None


def test_model_tablename_and_columns() -> None:
    from app.models.def_valueset_modelo_linha_operacao import (
        DefValuesetModeloLinhaOperacao,
    )

    assert (
        DefValuesetModeloLinhaOperacao.__tablename__
        == "def_valueset_modelo_linha_operacoes"
    )
    columns = set(DefValuesetModeloLinhaOperacao.__table__.columns.keys())
    expected = {
        "id",
        "def_valueset_modelo_linha_id",
        "def_operacao_id",
        "ordem",
        "regra_calculo",
        "quantidade_base",
        "tempo_setup_minutos",
        "tempo_por_unidade_minutos",
        "unidade_tempo",
        "obrigatorio",
        "ativo",
        "observacoes",
        "created_at",
        "updated_at",
    }
    assert expected <= columns


def test_model_foreign_keys_unique_and_cascade() -> None:
    from app.models.def_valueset_modelo_linha_operacao import (
        DefValuesetModeloLinhaOperacao,
    )

    table = DefValuesetModeloLinhaOperacao.__table__
    assert table.columns["def_valueset_modelo_linha_id"].nullable is False
    assert table.columns["def_operacao_id"].nullable is False

    fk_targets = {fk.column.table.name for fk in table.foreign_keys}
    assert {"def_valueset_modelo_linhas", "def_operacoes"} <= fk_targets
    linha_fk = next(
        fk
        for fk in table.foreign_keys
        if fk.column.table.name == "def_valueset_modelo_linhas"
    )
    assert linha_fk.ondelete == "CASCADE"

    # New CNC model: no unique constraint (several method links allowed);
    # a plain composite index replaces it.
    for constraint in table.constraints:
        assert constraint.__class__.__name__ != "UniqueConstraint"
    indexed = {tuple(c.name for c in index.columns) for index in table.indexes}
    assert ("def_valueset_modelo_linha_id", "def_operacao_id") in indexed
    assert ("metodo_calculo",) in indexed


def test_linha_has_operacoes_relationship_with_delete_orphan() -> None:
    from app.models.def_valueset_modelo_linha import DefValuesetModeloLinha

    relationship = DefValuesetModeloLinha.operacoes.property
    assert "delete-orphan" in relationship.cascade
    assert "delete" in relationship.cascade
