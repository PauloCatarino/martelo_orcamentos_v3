"""Per-line quantity computation for the costing table (phase 8T.4).

qt_total of a line = qt_mod_efetivo x qt_und, where qt_mod_efetivo is the qt_mod
of the DIVISAO_INDEPENDENTE line that governs the block above it (or the line's
own qt_mod when no division is active). A composite component (linha_pai set)
multiplies, além disso, pela quantidade de cada ancestral — e mais nada:

    qt total = qt mod  x  qt und do composto  x  qt und do componente

**Regra retirada (2026-08-05).** Havia aqui uma tentativa de adivinhar a "peça
principal" de uma composta — a PRIMEIRA peça estrutural da lista — e multiplicar
todos os outros componentes pela quantidade dela. Servia a porta dupla (2
portas por unidade => 2x as dobradiças), mas o código não distingue "2 portas
por unidade" de "2 lados por gaveta": numa gaveta, o primeiro componente é o
LADO_GAVETA com 2, e o fundo, a frente, a corrediça e o puxador vinham todos a
dobrar. Quantidades que dependem de uma peça (dobradiças por porta) configuram-se
**nessa peça**, não na composta — a expansão desce aos associados dela, como se
fez com as uniões nos topos, que passaram para o FUNDO_2000.

Pure and deterministic: the caller passes the lines in display (id) order.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from app.domain.custeio_linha_types import DIVISAO_INDEPENDENTE, SEPARADOR
from app.domain.medidas import normalizar_numero

_UM = Decimal("1")
_ZERO = Decimal("0")


@dataclass(frozen=True)
class LinhaQuantidade:
    """Minimal view of a cost line for the quantity computation."""

    id: int
    tipo_linha: str
    qt_mod: Decimal | None = None
    qt_und: Decimal | None = None
    linha_pai_id: int | None = None


@dataclass(frozen=True)
class ResultadoQuantidade:
    """Computed quantity of one line: the total and the display chain factors."""

    qt_total: Decimal
    cadeia: tuple[Decimal, ...]


def _num(valor) -> Decimal:
    """Normalise a quantity to a Decimal, defaulting missing/invalid to 1."""
    numero = normalizar_numero(valor)
    return numero if numero is not None else _UM


def calcular_quantidades(
    linhas: Sequence[LinhaQuantidade],
) -> dict[int, ResultadoQuantidade]:
    """Compute qt_total and the display chain of each line (in display order).

    Rules:
    - a DIVISAO_INDEPENDENTE line's qt_mod governs every line below it, until the
      next division (its own qt_total is just the module count);
    - a normal line: qt_total = qt_mod_efetivo x qt_und, where qt_mod_efetivo is
      the active division's qt_mod, or the line's own qt_mod when no division is
      active;
    - a composite component (linha_pai set): qt_total = qt_mod_efetivo x
      qt_und de cada ancestral x qt_und(componente).

    The lines MUST be given in display (id) order so each division governs the
    lines that follow it. Never raises.
    """
    por_id = {linha.id: linha for linha in linhas}
    qt_mod_divisao: Decimal | None = None
    resultado: dict[int, ResultadoQuantidade] = {}

    for linha in linhas:
        if linha.tipo_linha == SEPARADOR:
            # A separator is purely visual: it carries no quantity and does NOT
            # interrupt the active division block (qt_mod_divisao is preserved,
            # so the lines after it keep belonging to the division above).
            resultado[linha.id] = ResultadoQuantidade(qt_total=_ZERO, cadeia=())
            continue

        if linha.tipo_linha == DIVISAO_INDEPENDENTE:
            qt_mod_divisao = _num(linha.qt_mod)
            resultado[linha.id] = ResultadoQuantidade(
                qt_total=qt_mod_divisao, cadeia=(qt_mod_divisao,)
            )
            continue

        qt_und = _num(linha.qt_und)
        qt_mod_efetivo = (
            qt_mod_divisao if qt_mod_divisao is not None else _num(linha.qt_mod)
        )

        fatores_ancestrais: list[Decimal] = []
        pai_id = linha.linha_pai_id
        vistos: set[int] = set()
        while pai_id is not None and pai_id not in vistos:
            vistos.add(pai_id)
            pai = por_id.get(pai_id)
            if pai is None:
                break
            fatores_ancestrais.append(_num(pai.qt_und))
            pai_id = pai.linha_pai_id

        if fatores_ancestrais:
            fatores_ancestrais.reverse()
            qt_total = qt_mod_efetivo * qt_und
            for fator in fatores_ancestrais:
                qt_total *= fator
            cadeia = (qt_mod_efetivo, *fatores_ancestrais, qt_und)
        else:
            qt_total = qt_mod_efetivo * qt_und
            cadeia = (qt_mod_efetivo, qt_und)

        resultado[linha.id] = ResultadoQuantidade(qt_total=qt_total, cadeia=cadeia)

    return resultado


def _formatar_fator(valor: Decimal) -> str:
    """Format one chain factor: trim trailing zeros, comma as decimal separator."""
    texto = format(valor.normalize(), "f")
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    if texto == "-0":
        texto = "0"

    return texto.replace(".", ",")


def formatar_cadeia(cadeia: Sequence[Decimal], separador: str = " x ") -> str:
    """Format the quantity chain for display, e.g. (3, 1, 5) -> "3 x 1 x 5"."""
    return separador.join(_formatar_fator(fator) for fator in cadeia)
