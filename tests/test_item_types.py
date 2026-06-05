"""Tests for item type domain helpers."""

from __future__ import annotations

from app.domain.item_types import (
    COZINHA,
    MOVEL_WC,
    OUTRO,
    ROUPEIRO_ABRIR,
    ROUPEIRO_CORRER,
    get_item_type_label,
    get_item_type_options,
    normalize_item_type,
)


def test_item_type_labels() -> None:
    assert get_item_type_label(ROUPEIRO_ABRIR) == "Roupeiro Abrir"
    assert get_item_type_label(ROUPEIRO_CORRER) == "Roupeiro Correr"
    assert get_item_type_label(MOVEL_WC) == "M\u00f3vel WC"
    assert get_item_type_label(COZINHA) == "Cozinha"
    assert get_item_type_label(OUTRO) == "Outro"


def test_item_type_normalization() -> None:
    assert normalize_item_type("roupeiro_abrir") == ROUPEIRO_ABRIR
    assert normalize_item_type("") == OUTRO
    assert normalize_item_type(None) == OUTRO
    assert normalize_item_type("INVALIDO") == OUTRO
    assert get_item_type_label("INVALIDO") == "Outro"


def test_item_type_options() -> None:
    options = get_item_type_options()

    assert (ROUPEIRO_ABRIR, "Roupeiro Abrir") in options
    assert (ROUPEIRO_CORRER, "Roupeiro Correr") in options
    assert (MOVEL_WC, "M\u00f3vel WC") in options
    assert (COZINHA, "Cozinha") in options
    assert (OUTRO, "Outro") in options
