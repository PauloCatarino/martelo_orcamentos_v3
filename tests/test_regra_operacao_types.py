"""Tests for operation calculation rule helpers."""

from __future__ import annotations

from app.domain.regra_operacao_types import (
    FIXA,
    MANUAL,
    POR_AREA_FACE,
    POR_FURACAO,
    POR_M2,
    POR_ML,
    POR_ORLAS,
    POR_PECA,
    POR_QUANTIDADE,
    POR_SETUP,
    RASGO_CNC,
    get_regra_operacao_label,
    get_regra_operacao_options,
    normalize_regra_operacao,
)


def test_normalize_defaults_to_fixa() -> None:
    assert normalize_regra_operacao(None) == FIXA
    assert normalize_regra_operacao("") == FIXA
    assert normalize_regra_operacao("   ") == FIXA
    assert normalize_regra_operacao("desconhecida") == FIXA


def test_normalize_accepts_known_values_case_insensitive() -> None:
    assert normalize_regra_operacao("fixa") == FIXA
    assert normalize_regra_operacao(" por_peca ") == POR_PECA
    assert normalize_regra_operacao("por_m2") == POR_M2
    assert normalize_regra_operacao("POR_AREA_FACE") == POR_AREA_FACE
    assert normalize_regra_operacao("manual") == MANUAL


def test_labels_for_known_rules() -> None:
    assert get_regra_operacao_label(FIXA) == "Fixa"
    assert get_regra_operacao_label(POR_PECA) == "Por peça"
    assert get_regra_operacao_label(POR_QUANTIDADE) == "Por quantidade"
    assert get_regra_operacao_label(POR_ML) == "Por metro linear"
    assert get_regra_operacao_label(POR_M2) == "Por metro quadrado"
    assert get_regra_operacao_label(POR_AREA_FACE) == "Por área da face"
    assert get_regra_operacao_label(POR_ORLAS) == "Por orlas"
    assert get_regra_operacao_label(POR_FURACAO) == "Por furação"
    assert get_regra_operacao_label(POR_SETUP) == "Por setup"
    assert get_regra_operacao_label(MANUAL) == "Manual"


def test_label_uses_normalization() -> None:
    assert get_regra_operacao_label("xpto") == "Fixa"
    assert get_regra_operacao_label(None) == "Fixa"


def test_options_list_all_rules_in_order() -> None:
    options = get_regra_operacao_options()
    codes = [code for code, _ in options]

    assert codes == [
        FIXA,
        POR_PECA,
        POR_QUANTIDADE,
        POR_ML,
        POR_M2,
        POR_AREA_FACE,
        POR_ORLAS,
        POR_FURACAO,
        POR_SETUP,
        RASGO_CNC,
        MANUAL,
    ]
