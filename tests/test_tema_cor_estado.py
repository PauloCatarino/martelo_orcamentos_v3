"""Tests for budget status badge colours."""

from __future__ import annotations

from app.domain.orcamento_estados import ESTADOS_ORCAMENTO
from app.ui.tema import TEXTO_NORMAL, ZEBRA_ALT, cor_estado, cor_estado_producao


def test_cor_estado_devolve_cores_para_estados_conhecidos() -> None:
    for estado in ESTADOS_ORCAMENTO:
        fundo, texto = cor_estado(estado)

        assert fundo
        assert texto
        assert fundo.startswith("#")
        assert texto.startswith("#")


def test_cor_estado_e_case_insensitive() -> None:
    assert cor_estado("ENVIADO") == cor_estado("Enviado")


def test_cor_estado_tem_fallback_para_desconhecido() -> None:
    assert cor_estado("sem estado") == (ZEBRA_ALT, TEXTO_NORMAL)
    assert cor_estado(None) == (ZEBRA_ALT, TEXTO_NORMAL)


def test_cor_estado_producao_devolve_cores_para_estados_conhecidos() -> None:
    assert cor_estado_producao("Produção") == ("#FAEEDA", "#854F0B")
    assert cor_estado_producao("Arquivado") == ("#F1EFE8", "#2C2C2A")


def test_cor_estado_producao_tem_fallback_para_desconhecido() -> None:
    assert cor_estado_producao("sem estado") == ("", "")
