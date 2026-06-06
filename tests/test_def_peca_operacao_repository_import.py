"""Import checks for the DefPecaOperacao repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.def_peca_operacao_repository import (
        DefPecaOperacaoRepository,
        DefPecaOperacaoResumo,
    )

    assert DefPecaOperacaoRepository is not None
    assert DefPecaOperacaoResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.def_peca_operacao_repository import DefPecaOperacaoRepository

    for method in (
        "list_by_def_peca",
        "list_active_by_def_peca",
        "get_by_id",
        "create_peca_operacao",
        "update_peca_operacao",
        "deactivate_peca_operacao",
        "activate_peca_operacao",
    ):
        assert hasattr(DefPecaOperacaoRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.def_peca_operacao_repository import DefPecaOperacaoResumo

    field_names = {field.name for field in dataclasses.fields(DefPecaOperacaoResumo)}
    expected = {
        "id",
        "def_peca_id",
        "def_operacao_id",
        "ordem",
        "regra_calculo",
        "quantidade_base",
        "obrigatorio",
        "ativo",
        "observacoes",
    }
    assert expected <= field_names
