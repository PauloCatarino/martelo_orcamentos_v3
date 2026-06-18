"""Tests for canonical budget statuses."""

from __future__ import annotations

from app.domain.orcamento_estados import ESTADO_INICIAL, ESTADOS_ORCAMENTO


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
