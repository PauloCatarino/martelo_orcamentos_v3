"""Helpers for evaluating cost line measures, areas and perimeters.

This phase resolves only simple values: direct numbers, numeric strings (with
comma or dot) and single item variables (H/L/P and aliases). Complex formulas
(``H/2``, ``L-50`` ...) are intentionally left unresolved (return ``None``)
without raising, to be handled in a future phase.
"""

from __future__ import annotations

import ast
import re
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

# Explicit dimensions of the immediate parent piece/conjunto. They are reserved
# for formulas configured on DefPecaComponente and will be wired into costing in
# the next phase.
VARIAVEIS_PAI = ("PAI_COMP", "PAI_LARG", "PAI_ESP")

# Identifier tokens (variable names) inside a measure expression.
_TOKEN_VARIAVEL = re.compile(r"[A-Za-z_]\w*")


def expressao_usa_variaveis(texto) -> bool:
    """True when a measure expression contains variable tokens (H, L, HM, ...)."""
    return isinstance(texto, str) and bool(_TOKEN_VARIAVEL.search(texto))


def normalizar_variaveis_medida(texto):
    """Uppercase the variable letters of a measure expression text.

    Variable names (H, L, P, HM, L1, ...) are matched as identifier tokens and
    uppercased; numbers, operators and spacing are kept exactly as written.
    Non-string input is returned unchanged. The evaluator is already
    case-insensitive, so this only normalises the stored/displayed text
    ("l/5*2" -> "L/5*2", "hm-50" -> "HM-50").
    """
    if not isinstance(texto, str):
        return texto

    return _TOKEN_VARIAVEL.sub(lambda match: match.group(0).upper(), texto)


def normalizar_numero(valor) -> Decimal | None:
    """Convert a value into a Decimal, or None when it is not a clean number.

    Accepts Decimal/int/float and numeric strings using comma or dot.
    """
    if valor is None:
        return None

    if isinstance(valor, bool):
        return None

    if isinstance(valor, Decimal):
        return valor if valor.is_finite() else None

    if isinstance(valor, (int, float)):
        numero = Decimal(str(valor))
        return numero if numero.is_finite() else None

    if isinstance(valor, str):
        texto = valor.strip().replace(" ", "").replace(",", ".")
        if not texto:
            return None
        try:
            numero = Decimal(texto)
            return numero if numero.is_finite() else None
        except InvalidOperation:
            return None

    return None


def validar_expressao_medida(
    valor,
    contexto: dict | None = None,
    *,
    campo: str = "Medida",
    permitir_vazio: bool = True,
    permitir_variaveis_sem_valor: bool = False,
) -> tuple[str | None, Decimal | None]:
    """Normalize and validate one user-entered measure expression.

    Empty input is allowed by default because some costing line types do not
    use every measure. A non-empty input must use the supported expression
    grammar, resolve all its variables in ``contexto`` and produce a finite,
    strictly positive value. The normalized raw expression and evaluated value
    are returned together so callers cannot accidentally persist an expression
    they did not validate.
    """
    if valor is None or not str(valor).strip():
        if permitir_vazio:
            return None, None
        raise ValueError(f"{campo} é obrigatória.")

    texto = normalizar_variaveis_medida(str(valor).strip())
    resultado = avaliar_medida(texto, contexto)
    if resultado is None:
        if permitir_variaveis_sem_valor and _expressao_valida_com_placeholders(
            texto, contexto or {}
        ):
            return texto, None
        raise ValueError(
            f"{campo} inválida: use números, H/L/P ou HM/LM/PM "
            "com +, -, *, / e parênteses."
        )
    if not resultado.is_finite():
        raise ValueError(f"{campo} inválida: o resultado tem de ser finito.")
    if resultado <= 0:
        raise ValueError(f"{campo} inválida: o resultado tem de ser maior que zero.")

    return texto, resultado


def validar_formula_dimensional(
    valor,
    *,
    campo: str,
    permitir_pai: bool = False,
) -> str | None:
    """Validate and normalize a catalog dimensional formula.

    Catalog formulas have no real item dimensions while being edited, so known
    variables are evaluated with safe positive placeholders. Parent variables
    are accepted only for component transformations; header formulas must use
    the item/division context exclusively.
    """
    if valor is None or not str(valor).strip():
        return None

    texto = normalizar_variaveis_medida(str(valor).strip())
    permitidas = set(VARIAVEIS_ITEM) | set(VARIAVEIS_LOCAIS)
    if permitir_pai:
        permitidas.update(VARIAVEIS_PAI)
    usadas = {token.upper() for token in _TOKEN_VARIAVEL.findall(texto)}
    desconhecidas = sorted(usadas - permitidas)
    if desconhecidas:
        raise ValueError(
            f"{campo} inválida: variável não permitida {desconhecidas[0]}."
        )

    contexto = {variavel: Decimal("1000") for variavel in permitidas}
    resultado = avaliar_medida(texto, contexto)
    if resultado is None or not resultado.is_finite() or resultado <= 0:
        variaveis = "H/L/P, HM/LM/PM"
        if permitir_pai:
            variaveis += " ou PAI_COMP/PAI_LARG/PAI_ESP"
        raise ValueError(
            f"{campo} inválida: use números, {variaveis} com +, -, *, / e parênteses."
        )
    return texto


def _expressao_valida_com_placeholders(texto: str, contexto: dict) -> bool:
    """Distinguish known variables without values from an invalid expression.

    Costing reports intentionally support items whose base measures are still
    empty: H/L/P are known variables there, but cannot yet produce an area. For
    validation purposes only, missing known values are replaced by 1. Unknown
    names, bad syntax, disallowed operators and explicit division by zero still
    fail through the regular safe evaluator.
    """
    contexto_teste = {
        str(chave).upper(): (
            numero if (numero := normalizar_numero(valor)) is not None else Decimal("1")
        )
        for chave, valor in contexto.items()
    }
    return _avaliar_expressao(texto, contexto_teste) is not None


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
