"""Import checks for the budget item ValueSet line operation repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.orcamento_item_valueset_linha_operacao_repository import (
        OrcamentoItemValuesetLinhaOperacaoRepository,
        OrcamentoItemValuesetLinhaOperacaoResumo,
    )

    assert OrcamentoItemValuesetLinhaOperacaoRepository is not None
    assert OrcamentoItemValuesetLinhaOperacaoResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.orcamento_item_valueset_linha_operacao_repository import (
        OrcamentoItemValuesetLinhaOperacaoRepository,
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
        assert hasattr(OrcamentoItemValuesetLinhaOperacaoRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.orcamento_item_valueset_linha_operacao_repository import (
        OrcamentoItemValuesetLinhaOperacaoResumo,
    )

    field_names = {
        field.name for field in dataclasses.fields(OrcamentoItemValuesetLinhaOperacaoResumo)
    }
    expected = {
        "id",
        "orcamento_item_valueset_linha_id",
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
