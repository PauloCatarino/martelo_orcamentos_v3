"""Tests for cost line type helpers."""

from __future__ import annotations

from app.domain.custeio_linha_types import (
    ACABAMENTO,
    ACESSORIO,
    DIVISAO_INDEPENDENTE,
    FERRAGEM,
    MANUAL,
    MAO_OBRA,
    MAQUINA,
    MATERIAL_PECA,
    OPERACAO,
    OPERACAO_MANUAL,
    ORLA_PECA,
    OUTRO,
    PECA,
    PECA_COMPOSTA,
    SETUP,
    get_custeio_linha_type_label,
    get_custeio_linha_type_options,
    normalize_custeio_linha_type,
)


def test_normalize_defaults_to_outro() -> None:
    assert normalize_custeio_linha_type(None) == OUTRO
    assert normalize_custeio_linha_type("") == OUTRO
    assert normalize_custeio_linha_type("   ") == OUTRO
    assert normalize_custeio_linha_type("desconhecido") == OUTRO


def test_normalize_accepts_known_values_case_insensitive() -> None:
    assert normalize_custeio_linha_type("material_peca") == MATERIAL_PECA
    assert normalize_custeio_linha_type(" orla_peca ") == ORLA_PECA
    assert normalize_custeio_linha_type("OPERACAO") == OPERACAO
    assert normalize_custeio_linha_type("manual") == MANUAL


def test_labels_for_known_types() -> None:
    assert get_custeio_linha_type_label(PECA) == "Peça"
    assert get_custeio_linha_type_label(PECA_COMPOSTA) == "Peça composta"
    assert get_custeio_linha_type_label(DIVISAO_INDEPENDENTE) == "Divisão independente"
    assert get_custeio_linha_type_label(MATERIAL_PECA) == "Material da peça"
    assert get_custeio_linha_type_label(ORLA_PECA) == "Orla da peça"
    assert get_custeio_linha_type_label(FERRAGEM) == "Ferragem"
    assert get_custeio_linha_type_label(ACESSORIO) == "Acessório"
    assert get_custeio_linha_type_label(OPERACAO) == "Operação"
    assert get_custeio_linha_type_label(MAQUINA) == "Máquina"
    assert get_custeio_linha_type_label(ACABAMENTO) == "Acabamento"
    assert get_custeio_linha_type_label(MAO_OBRA) == "Mão de obra"
    assert get_custeio_linha_type_label(SETUP) == "Setup"
    assert get_custeio_linha_type_label(MANUAL) == "Manual"
    assert get_custeio_linha_type_label(OUTRO) == "Outro"


def test_label_uses_normalization() -> None:
    assert get_custeio_linha_type_label("xpto") == "Outro"
    assert get_custeio_linha_type_label(None) == "Outro"


def test_options_list_all_types_in_order() -> None:
    codes = [code for code, _ in get_custeio_linha_type_options()]

    assert codes == [
        PECA,
        PECA_COMPOSTA,
        DIVISAO_INDEPENDENTE,
        MATERIAL_PECA,
        ORLA_PECA,
        FERRAGEM,
        ACESSORIO,
        OPERACAO,
        MAQUINA,
        ACABAMENTO,
        MAO_OBRA,
        SETUP,
        MANUAL,
        OPERACAO_MANUAL,
        OUTRO,
    ]
