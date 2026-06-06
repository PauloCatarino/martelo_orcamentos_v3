"""Tests for the default system settings seed script."""

from __future__ import annotations

from scripts.create_default_system_settings import (
    DEFAULT_SYSTEM_SETTINGS,
    DefaultSystemSettingsResult,
)


def test_default_system_settings_constants_import() -> None:
    settings_by_key = {seed.chave: seed for seed in DEFAULT_SYSTEM_SETTINGS}

    assert "pasta_base_orcamentos" in settings_by_key
    assert "pasta_materias_primas" in settings_by_key
    assert "preencher_comp_larg_automaticamente" in settings_by_key
    assert settings_by_key["provedor_resposta_ia"].valor == "openai"
    assert settings_by_key["modelo_openai_texto"].valor == "gpt-4o-mini"
    assert settings_by_key["preencher_comp_larg_automaticamente"].valor == "ON"
    assert settings_by_key["pasta_base_orcamentos"].tipo == "pasta"
    assert settings_by_key["ficheiro_imos_msg"].tipo == "ficheiro"


def test_default_system_settings_result_dataclass() -> None:
    result = DefaultSystemSettingsResult(criadas=2, reutilizadas=18)

    assert result.criadas == 2
    assert result.reutilizadas == 18
