"""Configurable quantity-rule expression engine (phase 8T.5.0).

Evaluates a small, SAFE expression language (AST whitelist, never ``eval``) that
later computes the quantity of a hardware item from the main piece's
dimensions. The result is a non-negative integer (fractions are rounded UP, the
minimum is 0). On any problem (unknown variable, bad syntax, division by zero,
disallowed construct) it returns ``(None, motivo)`` so the UI can show the error
— it never raises.

Context variables (case-insensitive, exposed uppercase):
  COMP, LARG, ESP  -> the main piece's real dimensions (mm)
  QT_PAI           -> the main piece's quantity (per module)
  MEDIDA_TOPO      -> selected top measurement (mm)
  NUM_TOPOS        -> number of tops where the association is applied

Supported on top of +, -, *, /, parentheses:
  - integer division //                          (FloorDiv)
  - comparisons <, <=, >, >=, ==, !=             (chainable)
  - booleans and / or / not
  - ternary conditional  A if COND else B        (chainable)
  - whitelisted functions CEIL(x), FLOOR(x), MIN(a, b, ...), MAX(a, b, ...)
"""

from __future__ import annotations

import ast
import math
from decimal import Decimal

from app.domain.medidas import normalizar_numero

# Context variables and functions available in a rule expression (for the UI).
VARIAVEIS_REGRA = ("COMP", "LARG", "ESP", "QT_PAI", "MEDIDA_TOPO", "NUM_TOPOS")
FUNCOES_REGRA = ("CEIL", "FLOOR", "MIN", "MAX")

# Sample context used to validate an expression before saving it.
CONTEXTO_EXEMPLO: dict[str, Decimal] = {
    "COMP": Decimal("2000"),
    "LARG": Decimal("600"),
    "ESP": Decimal("19"),
    "QT_PAI": Decimal("1"),
    "MEDIDA_TOPO": Decimal("600"),
    "NUM_TOPOS": Decimal("1"),
}

# Whitelisted AST node types (defence-in-depth on top of the recursive walk).
_NOS_PERMITIDOS = (
    ast.Expression,
    ast.BinOp,
    ast.UnaryOp,
    ast.BoolOp,
    ast.Compare,
    ast.IfExp,
    ast.Call,
    ast.Name,
    ast.Constant,
    ast.Load,
    # Operators
    ast.Add,
    ast.Sub,
    ast.Mult,
    ast.Div,
    ast.FloorDiv,
    ast.USub,
    ast.UAdd,
    ast.Not,
    ast.And,
    ast.Or,
    ast.Lt,
    ast.LtE,
    ast.Gt,
    ast.GtE,
    ast.Eq,
    ast.NotEq,
)

_VARIAVEIS_TEXTO = ", ".join(VARIAVEIS_REGRA)
_FUNCOES_TEXTO = ", ".join(FUNCOES_REGRA)


class _ErroRegra(Exception):
    """Internal error carrying a user-facing reason."""

    def __init__(self, motivo: str) -> None:
        super().__init__(motivo)
        self.motivo = motivo


def avaliar_regra_quantidade(
    expressao, contexto: dict | None = None
) -> tuple[int | None, str | None]:
    """Evaluate a quantity-rule expression. Returns (quantidade, motivo).

    On success returns ``(int >= 0, None)`` (fractions rounded up, minimum 0).
    On any problem returns ``(None, motivo)`` with a friendly reason. Never
    raises.
    """
    if expressao is None or not str(expressao).strip():
        return None, "Expressão vazia."

    texto = str(expressao).strip()
    try:
        arvore = ast.parse(texto, mode="eval")
    except (SyntaxError, ValueError):
        return None, "Expressão inválida: erro de sintaxe."

    if not all(isinstance(no, _NOS_PERMITIDOS) for no in ast.walk(arvore)):
        return None, "Expressão inválida: contém elementos não permitidos."

    ctx = _normalizar_contexto(contexto)
    try:
        valor = _avaliar_no(arvore.body, ctx)
    except _ErroRegra as erro:
        return None, erro.motivo
    except ZeroDivisionError:
        return None, "Divisão por zero na expressão."
    except (TypeError, ValueError, ArithmeticError):
        return None, "Não foi possível avaliar a expressão."

    return _para_quantidade(valor), None


def _normalizar_contexto(contexto: dict | None) -> dict[str, Decimal]:
    """Uppercase the context keys and coerce the values to Decimal (None -> 0)."""
    ctx: dict[str, Decimal] = {}
    for chave, valor in (contexto or {}).items():
        numero = normalizar_numero(valor)
        ctx[str(chave).upper()] = numero if numero is not None else Decimal("0")

    return ctx


def _para_quantidade(valor) -> int:
    """Round a result up to a non-negative integer (booleans count as 0/1)."""
    numero = _num(valor)
    return max(0, math.ceil(numero))


def _num(valor) -> Decimal:
    """Coerce an evaluated value to a Decimal (bool -> 1/0)."""
    if isinstance(valor, bool):
        return Decimal("1") if valor else Decimal("0")
    if isinstance(valor, Decimal):
        return valor
    if isinstance(valor, (int, float)):
        return Decimal(str(valor))

    raise _ErroRegra("Valor não numérico na expressão.")


def _verdade(valor) -> bool:
    """Truthiness of an evaluated value (0 is False, like Python)."""
    if isinstance(valor, bool):
        return valor

    return _num(valor) != 0


def _avaliar_no(no, ctx: dict[str, Decimal]):
    """Recursively evaluate one whitelisted AST node into a Decimal or bool."""
    if isinstance(no, ast.BinOp):
        return _avaliar_binop(no, ctx)
    if isinstance(no, ast.UnaryOp):
        return _avaliar_unaryop(no, ctx)
    if isinstance(no, ast.BoolOp):
        valores = [_verdade(_avaliar_no(v, ctx)) for v in no.values]
        if isinstance(no.op, ast.And):
            return all(valores)
        if isinstance(no.op, ast.Or):
            return any(valores)
        raise _ErroRegra("Operação booleana não permitida.")
    if isinstance(no, ast.Compare):
        return _avaliar_comparacao(no, ctx)
    if isinstance(no, ast.IfExp):
        if _verdade(_avaliar_no(no.test, ctx)):
            return _avaliar_no(no.body, ctx)
        return _avaliar_no(no.orelse, ctx)
    if isinstance(no, ast.Call):
        return _avaliar_funcao(no, ctx)
    if isinstance(no, ast.Constant):
        if isinstance(no.value, bool):
            return no.value
        if isinstance(no.value, (int, float)):
            return Decimal(str(no.value))
        raise _ErroRegra("Valor constante não permitido na expressão.")
    if isinstance(no, ast.Name):
        chave = no.id.upper()
        if chave in ctx:
            return ctx[chave]
        raise _ErroRegra(
            f"Variável desconhecida: {no.id}. Disponíveis: {_VARIAVEIS_TEXTO}."
        )

    raise _ErroRegra("Elemento não permitido na expressão.")


def _avaliar_binop(no: ast.BinOp, ctx: dict[str, Decimal]) -> Decimal:
    """Evaluate an arithmetic binary operation."""
    esquerda = _num(_avaliar_no(no.left, ctx))
    direita = _num(_avaliar_no(no.right, ctx))
    op = no.op
    if isinstance(op, ast.Add):
        return esquerda + direita
    if isinstance(op, ast.Sub):
        return esquerda - direita
    if isinstance(op, ast.Mult):
        return esquerda * direita
    if isinstance(op, ast.Div):
        if direita == 0:
            raise ZeroDivisionError
        return esquerda / direita
    if isinstance(op, ast.FloorDiv):
        if direita == 0:
            raise ZeroDivisionError
        return esquerda // direita

    raise _ErroRegra("Operação aritmética não permitida.")


def _avaliar_unaryop(no: ast.UnaryOp, ctx: dict[str, Decimal]):
    """Evaluate a unary operation (-, +, not)."""
    if isinstance(no.op, ast.Not):
        return not _verdade(_avaliar_no(no.operand, ctx))

    operando = _num(_avaliar_no(no.operand, ctx))
    if isinstance(no.op, ast.USub):
        return -operando
    if isinstance(no.op, ast.UAdd):
        return operando

    raise _ErroRegra("Operação unária não permitida.")


def _avaliar_comparacao(no: ast.Compare, ctx: dict[str, Decimal]) -> bool:
    """Evaluate a (chainable) comparison into a boolean."""
    esquerda = _num(_avaliar_no(no.left, ctx))
    resultado = True
    for op, comparador in zip(no.ops, no.comparators):
        direita = _num(_avaliar_no(comparador, ctx))
        if isinstance(op, ast.Lt):
            ok = esquerda < direita
        elif isinstance(op, ast.LtE):
            ok = esquerda <= direita
        elif isinstance(op, ast.Gt):
            ok = esquerda > direita
        elif isinstance(op, ast.GtE):
            ok = esquerda >= direita
        elif isinstance(op, ast.Eq):
            ok = esquerda == direita
        elif isinstance(op, ast.NotEq):
            ok = esquerda != direita
        else:
            raise _ErroRegra("Comparação não permitida.")

        resultado = resultado and ok
        esquerda = direita

    return resultado


def _avaliar_funcao(no: ast.Call, ctx: dict[str, Decimal]) -> Decimal:
    """Evaluate a whitelisted function call (CEIL/FLOOR/MIN/MAX)."""
    if not isinstance(no.func, ast.Name):
        raise _ErroRegra("Chamada de função não permitida.")
    if no.keywords:
        raise _ErroRegra("As funções não aceitam argumentos nomeados.")

    nome = no.func.id.upper()
    if nome not in FUNCOES_REGRA:
        raise _ErroRegra(
            f"Função não permitida: {no.func.id}. Disponíveis: {_FUNCOES_TEXTO}."
        )

    args = [_num(_avaliar_no(arg, ctx)) for arg in no.args]

    if nome == "CEIL":
        _exigir_argumentos(args, 1, "CEIL")
        return Decimal(math.ceil(args[0]))
    if nome == "FLOOR":
        _exigir_argumentos(args, 1, "FLOOR")
        return Decimal(math.floor(args[0]))
    if nome == "MIN":
        if not args:
            raise _ErroRegra("MIN exige pelo menos 1 argumento.")
        return min(args)
    # MAX
    if not args:
        raise _ErroRegra("MAX exige pelo menos 1 argumento.")
    return max(args)


def _exigir_argumentos(args: list, esperado: int, nome: str) -> None:
    """Raise when a function did not receive exactly ``esperado`` arguments."""
    if len(args) != esperado:
        raise _ErroRegra(f"{nome} exige {esperado} argumento(s).")
