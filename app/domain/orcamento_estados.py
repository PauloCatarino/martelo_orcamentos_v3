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
ESTADO_ADJUDICADO = "Adjudicado"


def deve_avisar_cliente_phc(
    estado_anterior: str | None, novo_estado: str, cliente_temporario: bool
) -> bool:
    """True when a budget moves to Adjudicado with a temporary customer."""
    return (
        cliente_temporario
        and novo_estado == ESTADO_ADJUDICADO
        and (estado_anterior or "") != ESTADO_ADJUDICADO
    )
