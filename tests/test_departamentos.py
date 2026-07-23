"""Tests for the user department helpers."""

from __future__ import annotations

from app.domain.departamentos import (
    DEPARTAMENTOS,
    e_de_orcamentos,
    e_de_producao,
    normalizar_departamento,
)


def test_lista_inclui_as_areas_indicadas_pelo_paulo() -> None:
    assert "Orçamentação" in DEPARTAMENTOS
    assert "Preparação (desenhos)" in DEPARTAMENTOS
    assert "Assistente de produção" in DEPARTAMENTOS
    assert "Administrativa" in DEPARTAMENTOS
    assert "Expedição" in DEPARTAMENTOS


def test_normalizar_limpa_espacos_e_none() -> None:
    assert normalizar_departamento("  Expedição  ") == "Expedição"
    assert normalizar_departamento(None) == ""
    assert normalizar_departamento("") == ""


def test_preparacao_conta_como_producao() -> None:
    """Quem faz desenhos trabalha no separador Produção."""
    assert e_de_producao("Preparação (desenhos)") is True
    assert e_de_producao("Assistente de produção") is True
    assert e_de_producao("Expedição") is True
    assert e_de_producao("Orçamentação") is False


def test_orcamentacao_conta_como_orcamentos() -> None:
    assert e_de_orcamentos("Orçamentação") is True
    assert e_de_orcamentos("Preparação (desenhos)") is False


def test_acentos_e_maiusculas_nao_importam() -> None:
    assert e_de_producao("PREPARACAO (DESENHOS)") is True
    assert e_de_orcamentos("orcamentacao") is True


def test_area_desconhecida_nao_e_de_lado_nenhum() -> None:
    assert e_de_producao("Administrativa") is False
    assert e_de_orcamentos("Administrativa") is False
