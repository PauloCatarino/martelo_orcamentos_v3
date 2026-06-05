"""Tests for composite piece component type helpers."""

from __future__ import annotations

from app.domain.componente_types import (
    ACESSORIO,
    FERRAGEM,
    MAO_OBRA,
    OPERACAO,
    PECA,
    SPP,
    get_componente_type_label,
    get_componente_type_options,
    normalize_componente_type,
)


def test_normalize_componente_type_defaults_to_peca() -> None:
    assert normalize_componente_type(None) == PECA
    assert normalize_componente_type("") == PECA
    assert normalize_componente_type("desconhecido") == PECA


def test_normalize_componente_type_accepts_known_values() -> None:
    assert normalize_componente_type("peca") == PECA
    assert normalize_componente_type(" ferragem ") == FERRAGEM
    assert normalize_componente_type("acessorio") == ACESSORIO
    assert normalize_componente_type("spp") == SPP
    assert normalize_componente_type("operacao") == OPERACAO
    assert normalize_componente_type("mao_obra") == MAO_OBRA


def test_componente_type_labels_and_options() -> None:
    assert get_componente_type_label(PECA) == "Pe\u00e7a"
    assert get_componente_type_label(FERRAGEM) == "Ferragem"
    assert get_componente_type_label(ACESSORIO) == "Acess\u00f3rio"
    assert get_componente_type_label(SPP) == "SPP / Barra / ML"
    assert get_componente_type_label(OPERACAO) == "Opera\u00e7\u00e3o"
    assert get_componente_type_label(MAO_OBRA) == "M\u00e3o de obra"
    assert (PECA, "Pe\u00e7a") in get_componente_type_options()
    assert (MAO_OBRA, "M\u00e3o de obra") in get_componente_type_options()
