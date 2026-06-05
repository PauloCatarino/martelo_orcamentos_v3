"""Edge banding type constants, labels, and formatting helpers."""

from __future__ import annotations

SEM_ORLA = 0
ORLA_FINA = 1
ORLA_GROSSA = 2

ORLA_TYPE_LABELS = {
    SEM_ORLA: "Sem orla",
    ORLA_FINA: "Orla fina",
    ORLA_GROSSA: "Orla grossa",
}


def get_orla_type_label(valor: int | str | None) -> str:
    """Return a friendly label for an edge banding type."""
    return ORLA_TYPE_LABELS[normalize_orla_type(valor)]


def get_orla_type_options() -> tuple[tuple[int, str], ...]:
    """Return edge banding type options as code/label pairs."""
    return tuple(ORLA_TYPE_LABELS.items())


def normalize_orla_type(valor: int | str | None) -> int:
    """Normalize an edge banding value, falling back to SEM_ORLA."""
    if valor is None:
        return SEM_ORLA

    if isinstance(valor, str):
        normalized = valor.strip()
        if not normalized:
            return SEM_ORLA

        try:
            parsed = int(normalized)
        except ValueError:
            return SEM_ORLA

        return parsed if parsed in ORLA_TYPE_LABELS else SEM_ORLA

    if valor in ORLA_TYPE_LABELS:
        return valor

    return SEM_ORLA


def format_orla_code(
    orla_c1: int | str | None,
    orla_c2: int | str | None,
    orla_l1: int | str | None,
    orla_l2: int | str | None,
) -> str:
    """Format the four edge banding values as a visual code."""
    values = (
        normalize_orla_type(orla_c1),
        normalize_orla_type(orla_c2),
        normalize_orla_type(orla_l1),
        normalize_orla_type(orla_l2),
    )

    return f"[{values[0]}{values[1]}{values[2]}{values[3]}]"
