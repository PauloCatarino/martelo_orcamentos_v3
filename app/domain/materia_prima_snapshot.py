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

from decimal import Decimal


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


def preco_orla_m2(ref_orla: str | None, resolver) -> Decimal | None:
    """Return an orla catalog net price only when its source unit is M2.

    ValueSet snapshots intentionally store only EUR/m2. A legacy orla priced
    in ML is not copied into this field because doing so would mislabel the
    unit; the costing compatibility path can still use the original catalog
    price and unit explicitly.
    """
    if not ref_orla:
        return None

    orla = resolver(ref_orla)
    if orla is None:
        return None

    unidade = (getattr(orla, "unidade", None) or "").strip().upper()
    if unidade not in {"M2", "M²", "M2.", "MTQ", "METRO2", "M^2"}:
        return None

    return getattr(orla, "preco_liquido", None)


def precos_orlas_m2(materia, resolver) -> tuple[Decimal | None, Decimal | None]:
    """Resolve the fine/thick orla prices for a selected board snapshot."""
    return (
        preco_orla_m2(coresp_orla_0_4(materia), resolver),
        preco_orla_m2(coresp_orla_1_0(materia), resolver),
    )
