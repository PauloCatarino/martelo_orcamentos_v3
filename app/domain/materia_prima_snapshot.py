"""Resolve raw material snapshot values for ValueSet lines.

The raw material catalog keeps the normalized type/family in
``tipo_martelo`` / ``familia_martelo`` and the original (Excel) values in
``tipo_original_excel`` / ``familia_original_excel``. In the current data only
the original columns are populated (e.g. hardware/handles and boards), so we
fall back to them. Edge references (``coresp_orla_0_4`` / ``coresp_orla_1_0``)
are copied when the catalog provides those attributes.

Centralized here so every ValueSet line dialog (model, budget and item) copies
the same snapshot from a selected raw material.
"""

from __future__ import annotations


def _primeiro_preenchido(*valores) -> str | None:
    """Return the first non-empty value (stringwise), or None."""
    for valor in valores:
        if valor is not None and str(valor).strip():
            return valor

    return None


def tipo_materia_prima(materia) -> str | None:
    """Type, preferring the normalized value and falling back to the Excel one."""
    return _primeiro_preenchido(
        getattr(materia, "tipo_martelo", None),
        getattr(materia, "tipo_original_excel", None),
    )


def familia_materia_prima(materia) -> str | None:
    """Family, preferring the normalized value and falling back to the Excel one."""
    return _primeiro_preenchido(
        getattr(materia, "familia_martelo", None),
        getattr(materia, "familia_original_excel", None),
    )


def coresp_orla_0_4(materia) -> str | None:
    """Thin (0.4) edge reference, when the catalog provides it."""
    return _primeiro_preenchido(getattr(materia, "coresp_orla_0_4", None))


def coresp_orla_1_0(materia) -> str | None:
    """Thick (1.0) edge reference, when the catalog provides it."""
    return _primeiro_preenchido(getattr(materia, "coresp_orla_1_0", None))
