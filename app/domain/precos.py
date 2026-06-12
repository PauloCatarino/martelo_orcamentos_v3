"""Pure price-building helpers for budget items (phase 8T.0).

The item price is built from three cost blocks summed over the item's active
cost lines (honouring the same per-line exclusion flags used by custo_total):

- bloco_mp: raw materials (custo_mp + custo_orlas + custo_ferragem);
- bloco_producao: production (custo_producao);
- bloco_acabamento: finishing (custo_acabamento).

Each block gets its own margin, then the administrative costs and the profit
margin multiply the subtotal, and a manual per-item adjustment (EUR, may be
negative) is added:

    subtotal = bloco_mp x (1 + margem_mp)
             + bloco_producao x (1 + margem_mao_obra)
             + bloco_acabamento x (1 + margem_acabamentos)
    preco_unitario = subtotal x (1 + custos_administrativos)
                              x (1 + margem_lucro) + ajuste_eur

All margins are human percentages (15 = 15%), stored as entered. Everything
works in Decimal and never raises on missing values.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.medidas import normalizar_numero

_ZERO = Decimal("0")
_CEM = Decimal("100")


@dataclass(frozen=True)
class MargensOrcamento:
    """Margins of one budget version, as human percentages (15 = 15%)."""

    margem_lucro_pct: Decimal = _ZERO
    margem_mp_pct: Decimal = _ZERO
    margem_mao_obra_pct: Decimal = _ZERO
    margem_acabamentos_pct: Decimal = _ZERO
    custos_administrativos_pct: Decimal = _ZERO


@dataclass(frozen=True)
class BlocosCusto:
    """Cost blocks of one item (or one line) for 1 unit of the item.

    The ``parcela_*`` fields are the real summands behind each block (for the
    formula tooltips): bloco_mp = parcela_mp + parcela_orlas + parcela_ferragem
    and bloco_producao breaks down into corte/orlagem/CNC/montagem-manual (each
    already scaled by the line's fator série, so the parcels add up to the
    block).
    """

    bloco_mp: Decimal = _ZERO
    bloco_producao: Decimal = _ZERO
    bloco_acabamento: Decimal = _ZERO
    parcela_mp: Decimal = _ZERO
    parcela_orlas: Decimal = _ZERO
    parcela_ferragem: Decimal = _ZERO
    parcela_corte: Decimal = _ZERO
    parcela_orlagem: Decimal = _ZERO
    parcela_cnc: Decimal = _ZERO
    parcela_montagem_manual: Decimal = _ZERO

    @property
    def custo_produzido(self) -> Decimal:
        """Total produced cost (the price base before margins)."""
        return self.bloco_mp + self.bloco_producao + self.bloco_acabamento


def fator_margem(percentagem_humana) -> Decimal:
    """Return the multiplier (1 + pct/100) for a human percentage.

    Unlike waste percentages there is no fraction heuristic here: the margins
    panel always stores human percentages, so 0.5 means 0.5% (not 50%).
    None/invalid -> factor 1.
    """
    pct = normalizar_numero(percentagem_humana)
    if pct is None:
        return Decimal("1")

    return Decimal("1") + pct / _CEM


def blocos_custo_da_linha(
    *,
    custo_mp=None,
    custo_orlas=None,
    custo_ferragem=None,
    custo_acabamento=None,
    custo_producao=None,
    custo_corte=None,
    custo_orlagem=None,
    custo_cnc=None,
    custo_montagem_manual=None,
    fator_serie=None,
    excluir_mp: bool = False,
    excluir_orla: bool = False,
    excluir_ferragem: bool = False,
    excluir_acabamento: bool = False,
    excluir_producao: bool = False,
) -> BlocosCusto:
    """Split one cost line into the price blocks, honouring the exclusions.

    Same exclusion semantics as calcular_custo_total_linha: a True flag means
    the matching cost is NOT summed; missing costs count as 0. The production
    partials feed the display parcels only (bloco_producao keeps summing the
    stored custo_producao, which already carries the fator série); the parcels
    are scaled by the same factor so they add up to the block. Never raises.
    """

    def parcela(excluido: bool, custo) -> Decimal:
        if excluido:
            return _ZERO
        valor = normalizar_numero(custo)
        return valor if valor is not None else _ZERO

    parcela_mp = parcela(excluir_mp, custo_mp)
    parcela_orlas = parcela(excluir_orla, custo_orlas)
    parcela_ferragem = parcela(excluir_ferragem, custo_ferragem)

    fator = normalizar_numero(fator_serie)
    if fator is None or fator <= 0:
        fator = Decimal("1")

    return BlocosCusto(
        bloco_mp=parcela_mp + parcela_orlas + parcela_ferragem,
        bloco_producao=parcela(excluir_producao, custo_producao),
        bloco_acabamento=parcela(excluir_acabamento, custo_acabamento),
        parcela_mp=parcela_mp,
        parcela_orlas=parcela_orlas,
        parcela_ferragem=parcela_ferragem,
        parcela_corte=parcela(excluir_producao, custo_corte) * fator,
        parcela_orlagem=parcela(excluir_producao, custo_orlagem) * fator,
        parcela_cnc=parcela(excluir_producao, custo_cnc) * fator,
        parcela_montagem_manual=parcela(excluir_producao, custo_montagem_manual)
        * fator,
    )


def somar_blocos_custo(blocos) -> BlocosCusto:
    """Sum an iterable of BlocosCusto into the item's total blocks."""
    total = {
        "bloco_mp": _ZERO,
        "bloco_producao": _ZERO,
        "bloco_acabamento": _ZERO,
        "parcela_mp": _ZERO,
        "parcela_orlas": _ZERO,
        "parcela_ferragem": _ZERO,
        "parcela_corte": _ZERO,
        "parcela_orlagem": _ZERO,
        "parcela_cnc": _ZERO,
        "parcela_montagem_manual": _ZERO,
    }
    for bloco in blocos:
        for campo in total:
            total[campo] += getattr(bloco, campo)

    return BlocosCusto(**total)


def calcular_preco_unitario(
    blocos: BlocosCusto,
    margens: MargensOrcamento,
    ajuste_eur=None,
) -> Decimal:
    """Build the unit price of one item from its cost blocks and the margins.

    Full-precision result (no rounding); the caller decides where to quantize.
    A missing ajuste counts as 0.
    """
    subtotal = (
        blocos.bloco_mp * fator_margem(margens.margem_mp_pct)
        + blocos.bloco_producao * fator_margem(margens.margem_mao_obra_pct)
        + blocos.bloco_acabamento * fator_margem(margens.margem_acabamentos_pct)
    )
    preco = (
        subtotal
        * fator_margem(margens.custos_administrativos_pct)
        * fator_margem(margens.margem_lucro_pct)
    )

    ajuste = normalizar_numero(ajuste_eur)
    if ajuste is not None:
        preco += ajuste

    return preco


def calcular_preco_total(preco_unitario, quantidade) -> Decimal | None:
    """Return preco_unitario x quantidade (full precision), or None."""
    preco = normalizar_numero(preco_unitario)
    if preco is None:
        return None

    qt = normalizar_numero(quantidade)
    if qt is None:
        qt = Decimal("1")

    return preco * qt


def margem_lucro_efetiva_pct(preco_unitario, custo_produzido) -> Decimal | None:
    """Effective profit margin (%): (preco - custo) / custo x 100.

    None when either value is missing or the produced cost is 0 (an item
    without costs has no meaningful margin).
    """
    preco = normalizar_numero(preco_unitario)
    custo = normalizar_numero(custo_produzido)
    if preco is None or custo is None or custo == 0:
        return None

    return (preco - custo) / custo * _CEM
