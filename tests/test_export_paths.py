"""Testes (puros) das regras dos nomes de pasta da exportação (fase 8W.4.0)."""

from __future__ import annotations

from app.domain.export_paths import (
    escolher_nome_pasta,
    nome_pasta_orcamento,
    simplificar_cliente,
    subpasta_versao,
)


def test_simplificar_cliente_prioriza_nome_simplex():
    assert simplificar_cliente("JF VIVA", "Joao Ferreira") == "JF_VIVA"


def test_simplificar_cliente_troca_espacos_por_underscore():
    assert simplificar_cliente(None, "Maria do Carmo") == "MARIA_DO_CARMO"


def test_simplificar_cliente_fallback_quando_tudo_vazio():
    assert simplificar_cliente(None, None) == "CLIENTE"
    assert simplificar_cliente("", "  ") == "CLIENTE"


def test_subpasta_versao_dois_digitos():
    assert subpasta_versao(1) == "01"
    assert subpasta_versao(12) == "12"


def test_escolher_nome_pasta_reutiliza_existente_com_prefixo():
    existentes = ["outra_coisa", "260655_QUALQUER", "260999_X"]
    assert (
        escolher_nome_pasta(existentes, "260655", "JF VIVA", "Joao Ferreira")
        == "260655_QUALQUER"
    )


def test_escolher_nome_pasta_constroi_quando_nao_existe():
    assert (
        escolher_nome_pasta([], "260655", "JF VIVA", "Joao Ferreira")
        == "260655_JF_VIVA"
    )
    assert nome_pasta_orcamento("260655", "JF VIVA", "Joao Ferreira") == "260655_JF_VIVA"
