"""Import checks for the DefOperacao repository."""

from __future__ import annotations

import dataclasses


def test_repository_imports() -> None:
    from app.repositories.def_operacao_repository import DefOperacaoRepository, DefOperacaoResumo

    assert DefOperacaoRepository is not None
    assert DefOperacaoResumo is not None


def test_repository_has_expected_methods() -> None:
    from app.repositories.def_operacao_repository import DefOperacaoRepository

    for method in (
        "list_all",
        "list_active",
        "get_by_id",
        "get_by_codigo",
        "create_operacao",
        "update_operacao",
        "deactivate_operacao",
    ):
        assert hasattr(DefOperacaoRepository, method)


def test_resumo_has_expected_fields() -> None:
    from app.repositories.def_operacao_repository import DefOperacaoResumo

    field_names = {field.name for field in dataclasses.fields(DefOperacaoResumo)}
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
    }
    assert expected <= field_names


def test_resumo_embeds_real_machine_tariffs() -> None:
    """G2: the simulators read the machine's STD tariffs from the read model."""
    import inspect

    from app.repositories.def_operacao_repository import (
        DefOperacaoRepository,
        DefOperacaoResumo,
    )

    field_names = {field.name for field in dataclasses.fields(DefOperacaoResumo)}
    assert {
        "maquina_custo_hora_std",
        "maquina_custo_hora_serie",
        "maquina_preco_ml_std",
        "maquina_preco_lado_curto_std",
        "maquina_preco_lado_longo_std",
        "maquina_limite_lado_mm",
        "maquina_custo_setup_peca_std",
    } <= field_names

    source = inspect.getsource(DefOperacaoRepository._to_resumo)
    assert "custo_hora_serie" in source
    assert "preco_ml_std" in source
    assert "custo_setup_peca_std" in source
