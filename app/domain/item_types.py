"""Item type constants and labels."""

from __future__ import annotations

ROUPEIRO_ABRIR = "ROUPEIRO_ABRIR"
ROUPEIRO_CORRER = "ROUPEIRO_CORRER"
MOVEL_WC = "MOVEL_WC"
COZINHA = "COZINHA"
OUTRO = "OUTRO"

ITEM_TYPE_LABELS = {
    ROUPEIRO_ABRIR: "Roupeiro Abrir",
    ROUPEIRO_CORRER: "Roupeiro Correr",
    MOVEL_WC: "M\u00f3vel WC",
    COZINHA: "Cozinha",
    OUTRO: "Outro",
}


def get_item_type_label(tipo_item: str | None) -> str:
    """Return a friendly label for an item type."""
    return ITEM_TYPE_LABELS[normalize_item_type(tipo_item)]


def get_item_type_options() -> tuple[tuple[str, str], ...]:
    """Return item type options as code/label pairs."""
    return tuple(ITEM_TYPE_LABELS.items())


def normalize_item_type(tipo_item: str | None) -> str:
    """Normalize an item type code, falling back to OUTRO."""
    if not tipo_item:
        return OUTRO

    normalized = tipo_item.strip().upper()
    if normalized in ITEM_TYPE_LABELS:
        return normalized

    return OUTRO
