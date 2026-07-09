"""Import checks for OrcamentoValuesetLinhaOperacao model."""

from __future__ import annotations


def test_model_imports() -> None:
    from app.models.orcamento_valueset_linha_operacao import OrcamentoValuesetLinhaOperacao

    assert OrcamentoValuesetLinhaOperacao is not None


def test_model_is_registered_in_models() -> None:
    from app.models import OrcamentoValuesetLinhaOperacao

    assert OrcamentoValuesetLinhaOperacao is not None


def test_model_tablename_and_columns() -> None:
    from app.models.orcamento_valueset_linha_operacao import OrcamentoValuesetLinhaOperacao

    assert (
        OrcamentoValuesetLinhaOperacao.__tablename__ == "orcamento_valueset_linha_operacoes"
    )
    columns = set(OrcamentoValuesetLinhaOperacao.__table__.columns.keys())
    expected = {
        "id",
        "orcamento_valueset_linha_id",
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
    from app.models.orcamento_valueset_linha_operacao import OrcamentoValuesetLinhaOperacao

    table = OrcamentoValuesetLinhaOperacao.__table__
    assert table.columns["orcamento_valueset_linha_id"].nullable is False
    assert table.columns["def_operacao_id"].nullable is False

    fk_targets = {fk.column.table.name for fk in table.foreign_keys}
    assert {"orcamento_valueset_linhas", "def_operacoes"} <= fk_targets
    linha_fk = next(
        fk for fk in table.foreign_keys if fk.column.table.name == "orcamento_valueset_linhas"
    )
    assert linha_fk.ondelete == "CASCADE"

    unique_columns: set[str] = set()
    for constraint in table.constraints:
        if constraint.__class__.__name__ == "UniqueConstraint":
            unique_columns |= {column.name for column in constraint.columns}
    assert {"orcamento_valueset_linha_id", "def_operacao_id"} <= unique_columns


def test_linha_has_operacoes_relationship_with_delete_orphan() -> None:
    from app.models.orcamento_valueset_linha import OrcamentoValuesetLinha

    relationship = OrcamentoValuesetLinha.operacoes.property
    assert "delete-orphan" in relationship.cascade
    assert "delete" in relationship.cascade
