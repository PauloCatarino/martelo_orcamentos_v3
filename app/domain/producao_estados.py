"""Canonical production status values."""

from __future__ import annotations

import unicodedata

ESTADOS_PRODUCAO: tuple[str, ...] = (
    "Desenho",
    "Producao",
    "Finalizado",
    "Arquivado",
)

ESTADO_DESENHO = "Desenho"
ESTADO_PRODUCAO = "Producao"


def _normalizar(estado: object) -> str:
    """Compare states without caring about accents or capitals.

    Em obras antigas (e no que vem do PHC/Streamlit) aparece "Produção" com
    acento, por isso não se pode comparar o texto em bruto.
    """
    texto = unicodedata.normalize("NFKD", str(estado or "").strip())
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold()


def e_producao(estado: object) -> bool:
    """True when this state means the obra is in production."""
    return _normalizar(estado) == _normalizar(ESTADO_PRODUCAO)


def entra_em_producao(estado_anterior: object, estado_novo: object) -> bool:
    """True when the obra is moving into production from another state."""
    return e_producao(estado_novo) and not e_producao(estado_anterior)
