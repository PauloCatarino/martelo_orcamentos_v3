"""Import checks for the DefOperacao model."""

from __future__ import annotations


def test_def_operacao_model_imports() -> None:
    from app.models.def_operacao import DefOperacao

    assert DefOperacao is not None


def test_def_operacao_is_registered_in_models() -> None:
    from app.models import DefOperacao

    assert DefOperacao is not None


def test_def_operacao_tablename() -> None:
    from app.models.def_operacao import DefOperacao

    assert DefOperacao.__tablename__ == "def_operacoes"


def test_def_operacao_has_expected_columns() -> None:
    from app.models.def_operacao import DefOperacao

    columns = set(DefOperacao.__table__.columns.keys())
    expected = {
        "id",
        "codigo",
        "nome",
        "descricao",
        "tipo_operacao",
        "unidade_calculo",
        "tempo_base",
        "tempo_setup",
        "custo_hora",
        "custo_minimo",
        "maquina_id",
        "ativo",
        "observacoes",
        "created_at",
        "updated_at",
    }
    assert expected <= columns


def test_def_operacao_codigo_unique_indexes_and_fk() -> None:
    from app.models.def_operacao import DefOperacao

    table = DefOperacao.__table__

    unique_columns: set[str] = set()
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            unique_columns |= {column.name for column in constraint.columns}
    assert "codigo" in unique_columns

    indexed_columns = {tuple(column.name for column in index.columns) for index in table.indexes}
    assert ("tipo_operacao",) in indexed_columns
    assert ("unidade_calculo",) in indexed_columns
    assert ("ativo",) in indexed_columns
    assert ("maquina_id",) in indexed_columns

    fk_targets = {
        foreign_key.target_fullname
        for foreign_key in table.columns["maquina_id"].foreign_keys
    }
    assert "def_maquinas.id" in fk_targets
