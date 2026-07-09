"""Import checks for the budget version ValueSet line operation repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.orcamento_valueset_linha_operacao_repository import (
        OrcamentoValuesetLinhaOperacaoRepository,
        OrcamentoValuesetLinhaOperacaoResumo,
    )

    assert OrcamentoValuesetLinhaOperacaoRepository is not None
    assert OrcamentoValuesetLinhaOperacaoResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.orcamento_valueset_linha_operacao_repository import (
        OrcamentoValuesetLinhaOperacaoRepository,
    )

    for method in (
        "list_by_linha",
        "list_active_by_linha",
        "get_by_id",
        "create",
        "update",
        "deactivate",
        "activate",
        "delete_by_linha",
    ):
        assert hasattr(OrcamentoValuesetLinhaOperacaoRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.orcamento_valueset_linha_operacao_repository import (
        OrcamentoValuesetLinhaOperacaoResumo,
    )

    field_names = {
        field.name for field in dataclasses.fields(OrcamentoValuesetLinhaOperacaoResumo)
    }
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
    }
    assert expected <= field_names
