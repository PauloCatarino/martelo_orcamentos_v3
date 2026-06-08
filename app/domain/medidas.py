"""Helpers for evaluating cost line measures, areas and perimeters.

This phase resolves only simple values: direct numbers, numeric strings (with
comma or dot) and single item variables (H/L/P and aliases). Complex formulas
(``H/2``, ``L-50`` ...) are intentionally left unresolved (return ``None``)
without raising, to be handled in a future phase.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

# Item variable aliases accepted in a measure expression.
VARIAVEIS_ITEM = (
    "H",
    "COMP",
    "ALTURA",
    "ALTURA_COMP",
    "L",
    "LARG",
    "P",
    "PROF",
    "PROFUNDIDADE",
)


def normalizar_numero(valor) -> Decimal | None:
    """Convert a value into a Decimal, or None when it is not a clean number.

    Accepts Decimal/int/float and numeric strings using comma or dot.
    """
    if valor is None:
        return None

    if isinstance(valor, bool):
        return None

    if isinstance(valor, Decimal):
        return valor

    if isinstance(valor, (int, float)):
        return Decimal(str(valor))

    if isinstance(valor, str):
        texto = valor.strip().replace(" ", "").replace(",", ".")
        if not texto:
            return None
        try:
            return Decimal(texto)
        except InvalidOperation:
            return None

    return None


def construir_contexto_item(
    altura_comp, largura, profundidade
) -> dict[str, Decimal | None]:
    """Build the variable context from the item's main measures."""
    altura_comp = normalizar_numero(altura_comp)
    largura = normalizar_numero(largura)
    profundidade = normalizar_numero(profundidade)

    return {
        "H": altura_comp,
        "COMP": altura_comp,
        "ALTURA": altura_comp,
        "ALTURA_COMP": altura_comp,
        "L": largura,
        "LARG": largura,
        "P": profundidade,
        "PROF": profundidade,
        "PROFUNDIDADE": profundidade,
    }


def avaliar_medida(valor, contexto: dict | None = None) -> Decimal | None:
    """Evaluate one measure value.

    Returns None for empty/None/unresolved values (never raises). Resolves
    numbers, numeric strings and single item variables (H/L/P and aliases).
    """
    if valor is None:
        return None

    if isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float, Decimal)):
        return normalizar_numero(valor)

    if not isinstance(valor, str):
        return None

    texto = valor.strip()
    if not texto:
        return None

    chave = texto.upper()
    if contexto and chave in contexto:
        return normalizar_numero(contexto[chave])

    return normalizar_numero(texto)


def calcular_area_m2(comp_real, larg_real) -> Decimal | None:
    """Area in m^2 from two millimeter measures (comp * larg / 1_000_000)."""
    comp = normalizar_numero(comp_real)
    larg = normalizar_numero(larg_real)
    if comp is None or larg is None:
        return None

    return (comp * larg) / Decimal("1000000")


def calcular_perimetro_ml(comp_real, larg_real) -> Decimal | None:
    """Perimeter in ML from two millimeter measures (2 * (comp + larg) / 1000)."""
    comp = normalizar_numero(comp_real)
    larg = normalizar_numero(larg_real)
    if comp is None or larg is None:
        return None

    return (Decimal("2") * (comp + larg)) / Decimal("1000")
