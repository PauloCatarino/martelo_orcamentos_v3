"""Helpers for evaluating cost line measures, areas and perimeters.

This phase resolves only simple values: direct numbers, numeric strings (with
comma or dot) and single item variables (H/L/P and aliases). Complex formulas
(``H/2``, ``L-50`` ...) are intentionally left unresolved (return ``None``)
without raising, to be handled in a future phase.
"""

from __future__ import annotations

import ast
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

# Local (independent division / module) variable aliases. These only exist
# after an independent-division line and override nothing in the global context.
VARIAVEIS_LOCAIS = ("HM", "LM", "PM")


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


# AST node types allowed in a safe measure expression.
_NOS_PERMITIDOS = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.USub,
    ast.UAdd,
    ast.Constant,
    ast.Name,
    ast.Load,
)


def avaliar_medida(valor, contexto: dict | None = None) -> Decimal | None:
    """Evaluate one measure value.

    Returns None for empty/None/unresolved values (never raises). Resolves
    numbers, numeric strings, single variables (global H/L/P aliases and local
    HM/LM/PM) and simple math expressions (``H/2``, ``L*2``, ``(H-50)/2`` ...)
    using a safe AST evaluator (no eval). Unknown variables, invalid operations
    and division by zero all return None.
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

    contexto = contexto or {}

    # Single variable shortcut.
    chave = texto.upper()
    if chave in contexto:
        return normalizar_numero(contexto[chave])

    # Plain numeric value (handles comma decimals).
    numero = normalizar_numero(texto)
    if numero is not None:
        return numero

    # Safe math expression with variables.
    return _avaliar_expressao(texto, contexto)


def _avaliar_expressao(texto: str, contexto: dict) -> Decimal | None:
    """Evaluate a simple math expression safely, or None on any problem."""
    expressao = texto.replace(",", ".")
    try:
        arvore = ast.parse(expressao, mode="eval")
    except (SyntaxError, ValueError):
        return None

    if not all(isinstance(no, _NOS_PERMITIDOS) for no in ast.walk(arvore)):
        return None

    try:
        return _avaliar_no(arvore.body, contexto)
    except (TypeError, ValueError, ArithmeticError):
        return None


def _avaliar_no(no, contexto: dict) -> Decimal | None:
    """Recursively evaluate one whitelisted AST node into a Decimal or None."""
    if isinstance(no, ast.BinOp):
        esquerda = _avaliar_no(no.left, contexto)
        direita = _avaliar_no(no.right, contexto)
        if esquerda is None or direita is None:
            return None

        if isinstance(no.op, ast.Add):
            return esquerda + direita
        if isinstance(no.op, ast.Sub):
            return esquerda - direita
        if isinstance(no.op, ast.Mult):
            return esquerda * direita
        if isinstance(no.op, ast.Div):
            if direita == 0:
                return None
            return esquerda / direita
        return None

    if isinstance(no, ast.UnaryOp):
        operando = _avaliar_no(no.operand, contexto)
        if operando is None:
            return None
        if isinstance(no.op, ast.USub):
            return -operando
        if isinstance(no.op, ast.UAdd):
            return operando
        return None

    if isinstance(no, ast.Constant):
        if isinstance(no.value, bool):
            return None
        if isinstance(no.value, (int, float)):
            return Decimal(str(no.value))
        return None

    if isinstance(no, ast.Name):
        chave = no.id.upper()
        if chave in contexto:
            return normalizar_numero(contexto[chave])
        return None

    return None


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
