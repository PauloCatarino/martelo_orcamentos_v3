"""Tests for canonical budget statuses."""

from __future__ import annotations

from app.domain.orcamento_estados import (
    ESTADO_ADJUDICADO,
    ESTADO_INICIAL,
    ESTADOS_ORCAMENTO,
    deve_avisar_cliente_phc,
)


def test_estados_orcamento_tem_os_oito_valores_canonicos() -> None:
    assert ESTADOS_ORCAMENTO == (
        "Falta Or\u00e7amentar",
        "Enviado",
        "Conclu\u00eddo",
        "N\u00e3o Enviado",
        "Adjudicado",
        "Sem Interesse",
        "N\u00e3o Adjudicado",
        "Cancelado",
    )
    assert ESTADO_INICIAL == "Falta Or\u00e7amentar"
    assert "rascunho" not in ESTADOS_ORCAMENTO


def test_deve_avisar_ao_passar_a_adjudicado_com_cliente_temporario() -> None:
    assert (
        deve_avisar_cliente_phc("Falta Or\u00e7amentar", ESTADO_ADJUDICADO, True)
        is True
    )


def test_nao_avisa_se_ja_estava_adjudicado() -> None:
    assert (
        deve_avisar_cliente_phc(ESTADO_ADJUDICADO, ESTADO_ADJUDICADO, True)
        is False
    )


def test_nao_avisa_quando_cliente_e_phc() -> None:
    assert deve_avisar_cliente_phc("Enviado", ESTADO_ADJUDICADO, False) is False


def test_nao_avisa_noutros_estados() -> None:
    assert deve_avisar_cliente_phc("Falta Or\u00e7amentar", "Enviado", True) is False
