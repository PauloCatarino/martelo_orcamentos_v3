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


def test_normalize_valueset_key_defaults_to_material_outros_only_when_empty() -> None:
    assert normalize_valueset_key(None) == MATERIAL_OUTROS
    assert normalize_valueset_key("") == MATERIAL_OUTROS


def test_normalize_valueset_key_accepts_known_values_case_insensitive() -> None:
    assert normalize_valueset_key(" material_caixote ") == MATERIAL_CAIXOTE
    assert normalize_valueset_key("orla_fina") == ORLA_FINA


def test_normalize_valueset_key_preserves_custom_key() -> None:
    assert normalize_valueset_key(" niveladores/pendurais ") == "NIVELADORES/PENDURAIS"


def test_valueset_key_labels_and_options() -> None:
    assert get_valueset_key_label(FERRAGEM_DOBRADICA) == "Dobradiça"
    assert get_valueset_key_label("desconhecida") == "DESCONHECIDA"
    assert (MATERIAL_CAIXOTE, "Material caixote") in get_valueset_key_options()
    assert (FERRAGEM_DOBRADICA, "Dobradiça") in get_valueset_key_options()


def test_valueset_key_label_custom_key_returns_key_itself() -> None:
    assert get_valueset_key_label("NIVELADORES/PENDURAIS") == "NIVELADORES/PENDURAIS"


def test_new_valueset_keys_exist_and_normalize() -> None:
    from app.domain.valueset_types import (
        FERRAGEM_OUTRA,
        ILUMINACAO_CALHA_LED,
        ILUMINACAO_FITA_LED,
        ILUMINACAO_OUTRO,
        ILUMINACAO_SENSOR,
        ILUMINACAO_TRANSFORMADOR,
        MATERIAL_LATERAIS,
        MATERIAL_TAMPOS,
        SISTEMA_CORRER_CALHA_INF,
        SISTEMA_CORRER_CALHA_SUP,
        SISTEMA_CORRER_OUTRO,
        SISTEMA_CORRER_PUXADOR_WAVE,
        SISTEMA_CORRER_RODIZIO_INF,
        SISTEMA_CORRER_RODIZIO_SUP,
        VALUESET_KEY_LABELS,
    )

    novas_chaves = (
        MATERIAL_LATERAIS,
        MATERIAL_TAMPOS,
        FERRAGEM_OUTRA,
        SISTEMA_CORRER_RODIZIO_SUP,
        SISTEMA_CORRER_RODIZIO_INF,
        SISTEMA_CORRER_CALHA_SUP,
        SISTEMA_CORRER_CALHA_INF,
        SISTEMA_CORRER_PUXADOR_WAVE,
        SISTEMA_CORRER_OUTRO,
        ILUMINACAO_CALHA_LED,
        ILUMINACAO_FITA_LED,
        ILUMINACAO_TRANSFORMADOR,
        ILUMINACAO_SENSOR,
        ILUMINACAO_OUTRO,
    )

    for chave in novas_chaves:
        assert chave in VALUESET_KEY_LABELS
        assert normalize_valueset_key(chave) == chave


def test_material_laterais_label() -> None:
    from app.domain.valueset_types import MATERIAL_LATERAIS

    assert get_valueset_key_label(MATERIAL_LATERAIS) == "Material laterais"
