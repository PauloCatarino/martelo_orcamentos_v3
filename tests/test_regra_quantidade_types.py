"""Tests for component quantity rule helpers."""

from __future__ import annotations

from app.domain.regra_quantidade_types import (
    FIXA,
    MANUAL,
    POR_COMPRIMENTO,
    POR_COMPRIMENTO_LARGURA,
    POR_LARGURA,
    POR_QUANTIDADE_MODULO,
    POR_QUANTIDADE_PECA,
    get_regra_quantidade_label,
    get_regra_quantidade_options,
    normalize_regra_quantidade,
)


def test_normalize_defaults_to_fixa() -> None:
    assert normalize_regra_quantidade(None) == FIXA
    assert normalize_regra_quantidade("") == FIXA
    assert normalize_regra_quantidade("   ") == FIXA
    assert normalize_regra_quantidade("desconhecida") == FIXA


def test_normalize_accepts_known_values_case_insensitive() -> None:
    assert normalize_regra_quantidade("fixa") == FIXA
    assert normalize_regra_quantidade(" manual ") == MANUAL
    assert normalize_regra_quantidade("por_comprimento") == POR_COMPRIMENTO
    assert normalize_regra_quantidade("POR_COMPRIMENTO_LARGURA") == POR_COMPRIMENTO_LARGURA
    assert normalize_regra_quantidade(" por_largura ") == POR_LARGURA
    assert normalize_regra_quantidade("por_quantidade_peca") == POR_QUANTIDADE_PECA
    assert normalize_regra_quantidade("por_quantidade_modulo") == POR_QUANTIDADE_MODULO


def test_normalize_converts_legacy_altura_aliases() -> None:
    assert normalize_regra_quantidade("POR_ALTURA") == POR_COMPRIMENTO
    assert normalize_regra_quantidade(" por_altura ") == POR_COMPRIMENTO
    assert normalize_regra_quantidade("POR_ALTURA_LARGURA") == POR_COMPRIMENTO_LARGURA
    assert normalize_regra_quantidade("por_altura_largura") == POR_COMPRIMENTO_LARGURA


def test_labels_for_known_rules() -> None:
    assert get_regra_quantidade_label(FIXA) == "Fixa"
    assert get_regra_quantidade_label(MANUAL) == "Manual"
    assert get_regra_quantidade_label(POR_COMPRIMENTO) == "Por comprimento"
    assert get_regra_quantidade_label(POR_LARGURA) == "Por largura"
    assert get_regra_quantidade_label(POR_COMPRIMENTO_LARGURA) == "Por comprimento e largura"
    assert get_regra_quantidade_label(POR_QUANTIDADE_PECA) == "Por quantidade da peça principal"
    assert get_regra_quantidade_label(POR_QUANTIDADE_MODULO) == "Por quantidade do módulo"


def test_label_uses_normalization() -> None:
    assert get_regra_quantidade_label("POR_ALTURA") == "Por comprimento"
    assert get_regra_quantidade_label("xpto") == "Fixa"
    assert get_regra_quantidade_label(None) == "Fixa"


def test_options_list_all_rules_in_order_without_altura() -> None:
    options = get_regra_quantidade_options()
    codes = [code for code, _ in options]

    assert codes == [
        FIXA,
        MANUAL,
        POR_COMPRIMENTO,
        POR_LARGURA,
        POR_COMPRIMENTO_LARGURA,
        POR_QUANTIDADE_PECA,
        POR_QUANTIDADE_MODULO,
    ]
    for code, label in options:
        assert "ALTURA" not in code
        assert "altura" not in label.lower()
