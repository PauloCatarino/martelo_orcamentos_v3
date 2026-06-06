"""Tests for ValueSet key helpers."""

from __future__ import annotations

from app.domain.valueset_types import (
    FERRAGEM_DOBRADICA,
    MATERIAL_CAIXOTE,
    MATERIAL_OUTROS,
    ORLA_FINA,
    get_valueset_key_label,
    get_valueset_key_options,
    normalize_valueset_key,
)


def test_normalize_valueset_key_defaults_to_material_outros() -> None:
    assert normalize_valueset_key(None) == MATERIAL_OUTROS
    assert normalize_valueset_key("") == MATERIAL_OUTROS
    assert normalize_valueset_key("desconhecida") == MATERIAL_OUTROS


def test_normalize_valueset_key_accepts_known_values_case_insensitive() -> None:
    assert normalize_valueset_key(" material_caixote ") == MATERIAL_CAIXOTE
    assert normalize_valueset_key("orla_fina") == ORLA_FINA


def test_valueset_key_labels_and_options() -> None:
    assert get_valueset_key_label(FERRAGEM_DOBRADICA) == "Dobradiça"
    assert get_valueset_key_label("desconhecida") == "Material outros"
    assert (MATERIAL_CAIXOTE, "Material caixote") in get_valueset_key_options()
    assert (FERRAGEM_DOBRADICA, "Dobradiça") in get_valueset_key_options()
