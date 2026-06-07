"""Tests for the default ValueSet keys seed script."""

from __future__ import annotations

from scripts.create_default_valueset_chaves import (
    DEFAULT_VALUESET_CHAVES,
    ChaveSeed,
    DefaultValuesetChavesResult,
)


def test_seed_imports() -> None:
    assert len(DEFAULT_VALUESET_CHAVES) > 0


def test_seed_entries_have_structure() -> None:
    for seed in DEFAULT_VALUESET_CHAVES:
        assert isinstance(seed, ChaveSeed)
        assert seed.codigo.strip()
        assert seed.nome.strip()
        assert seed.tipo.strip()
        assert seed.grupo.strip()


def test_seed_codes_are_unique() -> None:
    codigos = [seed.codigo for seed in DEFAULT_VALUESET_CHAVES]

    assert len(codigos) == len(set(codigos))


def test_seed_main_types_and_groups_exist() -> None:
    tipos = {seed.tipo for seed in DEFAULT_VALUESET_CHAVES}
    grupos = {seed.grupo for seed in DEFAULT_VALUESET_CHAVES}

    assert {
        "MATERIAL",
        "FERRAGEM",
        "SISTEMA_CORRER",
        "ILUMINACAO",
        "ORLA",
        "ACABAMENTO",
        "ACESSORIO",
    } <= tipos
    assert {
        "MATERIAIS",
        "FERRAGENS",
        "SISTEMAS_CORRER",
        "ILUMINACAO",
        "ORLAS",
        "ACABAMENTOS",
        "ACESSORIOS",
    } <= grupos


def test_seed_contains_key_examples() -> None:
    codigos = {seed.codigo for seed in DEFAULT_VALUESET_CHAVES}

    assert "MATERIAL_PORTAS" in codigos
    assert "FERRAGEM_CORREDICA" in codigos
    assert "ACABAMENTO_FACE_SUP" in codigos


def test_result_dataclass() -> None:
    result = DefaultValuesetChavesResult(criadas=3, reutilizadas=2)

    assert result.criadas == 3
    assert result.reutilizadas == 2
