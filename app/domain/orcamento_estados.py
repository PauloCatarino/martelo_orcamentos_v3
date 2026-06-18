"""Canonical budget status values."""

from __future__ import annotations

ESTADOS_ORCAMENTO: tuple[str, ...] = (
    "Falta Or\u00e7amentar",
    "Enviado",
    "Conclu\u00eddo",
    "N\u00e3o Enviado",
    "Adjudicado",
    "Sem Interesse",
    "N\u00e3o Adjudicado",
    "Cancelado",
)
ESTADO_INICIAL = "Falta Or\u00e7amentar"
