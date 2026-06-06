"""Tests for operation type domain helpers."""

from __future__ import annotations


def test_operacao_type_options_include_expected_codes() -> None:
    from app.domain.operacao_types import (
        CNC,
        CORTE,
        MAO_OBRA,
        MANUAL,
        ORLAGEM,
        OUTRO,
        get_operacao_type_options,
    )

    codes = {code for code, _label in get_operacao_type_options()}

    assert {CORTE, ORLAGEM, CNC, MAO_OBRA, MANUAL, OUTRO} <= codes


def test_get_operacao_type_label() -> None:
    from app.domain.operacao_types import get_operacao_type_label

    assert get_operacao_type_label("CORTE") == "Corte"
    assert get_operacao_type_label("cnc") == "CNC / Mecaniza\u00e7\u00e3o"
    assert get_operacao_type_label("MAO_OBRA") == "M\u00e3o de obra"


def test_normalize_operacao_type_fallback() -> None:
    from app.domain.operacao_types import OUTRO, normalize_operacao_type

    assert normalize_operacao_type(None) == OUTRO
    assert normalize_operacao_type("") == OUTRO
    assert normalize_operacao_type(" desconhecido ") == OUTRO
    assert normalize_operacao_type(" corte ") == "CORTE"
