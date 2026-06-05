"""Tests for piece definition type helpers."""

from __future__ import annotations

from app.domain.peca_types import (
    COMPOSTA,
    SIMPLES,
    get_peca_type_label,
    get_peca_type_options,
    normalize_peca_type,
)


def test_normalize_peca_type_defaults_to_simples() -> None:
    assert normalize_peca_type(None) == SIMPLES
    assert normalize_peca_type("") == SIMPLES
    assert normalize_peca_type("desconhecido") == SIMPLES


def test_normalize_peca_type_accepts_known_values() -> None:
    assert normalize_peca_type("simples") == SIMPLES
    assert normalize_peca_type(" composta ") == COMPOSTA


def test_peca_type_labels_and_options() -> None:
    assert get_peca_type_label(SIMPLES) == "Simples"
    assert get_peca_type_label(COMPOSTA) == "Composta"
    assert (SIMPLES, "Simples") in get_peca_type_options()
    assert (COMPOSTA, "Composta") in get_peca_type_options()
