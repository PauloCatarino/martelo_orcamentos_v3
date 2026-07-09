"""Import checks for the ValueSet model line operation repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.def_valueset_modelo_linha_operacao_repository import (
        DefValuesetModeloLinhaOperacaoRepository,
        DefValuesetModeloLinhaOperacaoResumo,
    )

    assert DefValuesetModeloLinhaOperacaoRepository is not None
    assert DefValuesetModeloLinhaOperacaoResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.def_valueset_modelo_linha_operacao_repository import (
        DefValuesetModeloLinhaOperacaoRepository,
    )

    for method in (
        "list_by_linha",
        "list_active_by_linha",
        "get_by_id",
        "create",
        "update",
        "deactivate",
        "activate",
    ):
        assert hasattr(DefValuesetModeloLinhaOperacaoRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.def_valueset_modelo_linha_operacao_repository import (
        DefValuesetModeloLinhaOperacaoResumo,
    )

    field_names = {
        field.name for field in dataclasses.fields(DefValuesetModeloLinhaOperacaoResumo)
    }
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
    }
    assert expected <= field_names
