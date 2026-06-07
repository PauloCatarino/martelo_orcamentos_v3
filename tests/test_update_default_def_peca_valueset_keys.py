"""Tests for the def_peca ValueSet keys update script."""

from __future__ import annotations

from app.domain.valueset_types import VALUESET_KEY_LABELS
from scripts.update_default_def_peca_valueset_keys import (
    DEFAULT_DEF_PECA_VALUESET_KEYS,
    DefPecaValuesetSeed,
    UpdateValuesetKeysResult,
)


def test_mapping_imports() -> None:
    assert len(DEFAULT_DEF_PECA_VALUESET_KEYS) > 0


def test_mapping_covers_expected_pieces() -> None:
    assert {
        "COSTA",
        "LATERAL",
        "TAMPO",
        "FUNDO",
        "PORTA",
        "PORTA_SIMPLES",
        "PRATELEIRA",
        "PRATELEIRA_AMOVIVEL",
        "FRENTE_GAVETA",
        "LADO_GAVETA",
        "FUNDO_GAVETA",
        "TRASEIRA_GAVETA",
        "GAVETA",
    } <= set(DEFAULT_DEF_PECA_VALUESET_KEYS)


def test_material_keys_are_valid() -> None:
    for seed in DEFAULT_DEF_PECA_VALUESET_KEYS.values():
        assert seed.chave_valueset_material in VALUESET_KEY_LABELS


def test_no_empty_codes() -> None:
    for codigo, seed in DEFAULT_DEF_PECA_VALUESET_KEYS.items():
        assert codigo.strip()
        assert seed.chave_valueset_material.strip()


def test_pieces_with_acabamento_have_keys() -> None:
    for seed in DEFAULT_DEF_PECA_VALUESET_KEYS.values():
        if seed.permite_acabamento:
            assert seed.chave_valueset_acabamento_sup in VALUESET_KEY_LABELS
            assert seed.chave_valueset_acabamento_inf in VALUESET_KEY_LABELS
        else:
            assert seed.chave_valueset_acabamento_sup is None
            assert seed.chave_valueset_acabamento_inf is None


def test_specific_mappings() -> None:
    mapping = DEFAULT_DEF_PECA_VALUESET_KEYS

    assert mapping["COSTA"].chave_valueset_material == "MATERIAL_COSTAS"
    assert mapping["LATERAL"].chave_valueset_material == "MATERIAL_CAIXOTE"
    assert mapping["TAMPO"].chave_valueset_material == "MATERIAL_CAIXOTE"
    assert mapping["FUNDO"].chave_valueset_material == "MATERIAL_FUNDOS"
    assert mapping["PRATELEIRA"].chave_valueset_material == "MATERIAL_PRATELEIRAS"
    assert mapping["LADO_GAVETA"].chave_valueset_material == "MATERIAL_GAVETAS"

    assert mapping["LATERAL"].permite_acabamento is False
    assert mapping["PORTA"].permite_acabamento is True
    assert mapping["PORTA"].chave_valueset_acabamento_sup == "ACABAMENTO_FACE_SUP"
    assert mapping["PORTA"].chave_valueset_acabamento_inf == "ACABAMENTO_FACE_INF"
    assert mapping["FRENTE_GAVETA"].permite_acabamento is True


def test_result_dataclass() -> None:
    result = UpdateValuesetKeysResult(
        atualizadas=3,
        ignoradas_existentes=2,
        pecas_nao_encontradas=1,
    )

    assert result.atualizadas == 3
    assert result.ignoradas_existentes == 2
    assert result.pecas_nao_encontradas == 1


def test_seed_dataclass_defaults() -> None:
    seed = DefPecaValuesetSeed("MATERIAL_CAIXOTE")

    assert seed.permite_acabamento is False
    assert seed.chave_valueset_acabamento_sup is None
    assert seed.chave_valueset_acabamento_inf is None
