"""Tests for the hardware-category reset script."""

from __future__ import annotations

from scripts.reset_ferragens_categorias import (
    GENERIC_CATEGORIAS,
    NEW_VALUESET_CHAVES,
    OLD_FERRAGEM_VARIANT_CODES,
    OPERACOES_BASE,
    CategoriaPecaSeed,
    ChaveSeed,
    OperacaoBaseSeed,
    ResetFerragensResult,
)


def test_old_codes_are_explicit_and_do_not_touch_kept_rows() -> None:
    codigos = set(OLD_FERRAGEM_VARIANT_CODES)

    assert "CORREDICA LIVRE_1" in codigos
    assert "DOBRADICA_RETA" in codigos
    assert "VARAO+SUPORTES" in codigos
    assert "PORTA+DOBRADICA" in codigos
    assert "NIVELADORES/PENDURAIS" not in codigos
    assert "OPERACAO_MANUAL" not in codigos


def test_new_valueset_keys_have_expected_types_and_groups() -> None:
    chaves = {seed.codigo: seed for seed in NEW_VALUESET_CHAVES}

    assert all(isinstance(seed, ChaveSeed) for seed in NEW_VALUESET_CHAVES)
    assert chaves["FERRAGEM_SUPORTE_PRATELEIRA"].tipo == "FERRAGEM"
    assert chaves["FERRAGEM_AVENTOS"].grupo == "FERRAGENS"
    assert chaves["ILUMINACAO_CABO_LED"].tipo == "ILUMINACAO"
    assert chaves["SISTEMA_CORRER_CALHA_U"].tipo == "SISTEMA_CORRER"


def test_generic_categories_cover_requested_codes() -> None:
    categorias = {seed.codigo: seed for seed in GENERIC_CATEGORIAS}

    assert all(isinstance(seed, CategoriaPecaSeed) for seed in GENERIC_CATEGORIAS)
    assert categorias["DOBRADICA"].chave_valueset_material == "FERRAGEM_DOBRADICA"
    assert categorias["SUPORTE_VARAO"].grupo == "FERRAGENS"
    assert categorias["CABO_LED"].grupo == "ILUMINACAO"
    assert categorias["CALHA_PORTA_CORRER_H"].grupo == "SISTEMAS_CORRER"
    assert len(categorias) == len(GENERIC_CATEGORIAS)


def test_base_operations_are_limited_to_clear_categories() -> None:
    ligacoes = {(seed.peca_codigo, seed.operacao_codigo): seed for seed in OPERACOES_BASE}

    assert all(isinstance(seed, OperacaoBaseSeed) for seed in OPERACOES_BASE)
    assert ("DOBRADICA", "CNC_VERTICAL") in ligacoes
    assert ("CORREDICA", "CNC_VERTICAL") in ligacoes
    assert ("PUXADOR", "CNC_VERTICAL") in ligacoes
    assert ("VARAO", "OPERACAO_MANUAL") in ligacoes
    assert ligacoes[("VARAO", "OPERACAO_MANUAL")].unidade_tempo == "PECA"


def test_result_dataclass() -> None:
    result = ResetFerragensResult(
        dry_run=True,
        pecas_removidas=1,
        operacoes_removidas=2,
        componentes_removidos=3,
        linhas_custeio_removidas=4,
        linhas_modulo_removidas=5,
        chaves_criadas=6,
        chaves_reutilizadas=7,
        categorias_criadas=8,
        categorias_reutilizadas=9,
        ligacoes_criadas=10,
        ligacoes_reutilizadas=11,
        pecas_operacao_nao_encontradas=12,
        operacoes_nao_encontradas=13,
    )

    assert result.dry_run is True
    assert result.pecas_removidas == 1
    assert result.ligacoes_criadas == 10
