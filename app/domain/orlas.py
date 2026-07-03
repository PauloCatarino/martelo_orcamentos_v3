"""Helpers for computing edge banding (orlas) per cost line.

The orla code is four digits in the order ``C1 C2 L1 L2`` (matching
``app.domain.orla_types.format_orla_code``):

- C1/C2 are the two length sides and use ``comp_real``;
- L1/L2 are the two width sides and use ``larg_real``.

Each digit type is centralized in ``app.domain.orla_types``:
``0 = sem orla``, ``1 = orla fina`` (ref ``coresp_orla_0_4``),
``2 = orla grossa`` (ref ``coresp_orla_1_0``). Change it there to change the
meaning everywhere.

ML are measured per linear metre; each banded side adds the edge-bander safety
margin (``MARGEM_ORLADORA_POR_LADO_MM`` = +50 mm before + +50 mm after). Cost
uses the orla roll width chosen from ``esp_real`` and converts the raw material
M2 price into a per-ML price.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.domain.medidas import normalizar_numero
from app.domain.orla_types import ORLA_FINA, ORLA_GROSSA

# Edge-bander margin added to each banded side (mm): +50 before + +50 after.
MARGEM_ORLADORA_POR_LADO_MM = Decimal("100")

# Standard orla roll widths (mm).
LARGURAS_STANDARD_ORLA = (
    Decimal("19"),
    Decimal("22"),
    Decimal("25"),
    Decimal("28"),
    Decimal("33"),
    Decimal("35"),
    Decimal("43"),
    Decimal("45"),
    Decimal("48"),
    Decimal("55"),
    Decimal("60"),
)
# Minimum safety margin of the roll over the piece thickness (mm).
MARGEM_MINIMA_ESPESSURA_MM = Decimal("3")
# Extra width for pieces thicker than the largest standard roll (mm).
MARGEM_LARGURA_ACIMA_60_MM = Decimal("10")

AVISO_UNIDADE_ORLA = "Custo de orla não calculado: unidade da orla não validada."
AVISO_ESPESSURA_ORLA = "Custo de orla não calculado: espessura da peça em falta."


@dataclass(frozen=True)
class LadoOrla:
    """One side of a piece and its edge banding detail (prepared for the future)."""

    nome: str
    tipo: int
    medida_base_mm: Decimal | None
    medida_com_margem_mm: Decimal | None
    ml: Decimal | None
    referencia: str | None
    largura_orla_mm: Decimal | None
    preco: Decimal | None
    preco_ml: Decimal | None
    custo: Decimal | None


@dataclass(frozen=True)
class ResultadoOrlas:
    """Aggregated edge banding result for one cost line."""

    ml_orla_fina: Decimal | None
    ml_orla_grossa: Decimal | None
    custo_orla_fina: Decimal | None
    custo_orla_grossa: Decimal | None
    custo_orlas: Decimal | None
    largura_orla_mm: Decimal | None
    aviso: str | None
    lados: tuple[LadoOrla, ...]


def digitos_orla(codigo_orlas) -> tuple[int, int, int, int] | None:
    """Return the four side codes (C1, C2, L1, L2) or None when invalid."""
    if codigo_orlas is None:
        return None

    texto = str(codigo_orlas).strip().strip("[]")
    if len(texto) != 4 or not texto.isdigit():
        return None

    return tuple(int(digito) for digito in texto)  # type: ignore[return-value]


def selecionar_largura_orla_mm(esp_real) -> Decimal | None:
    """Choose the orla roll width (mm) for a given real thickness.

    For ``esp_real <= 60``: the smallest standard width >= ``esp_real + 3``.
    For ``esp_real > 60`` (or when no standard fits): ``esp_real + 10``.
    """
    esp = normalizar_numero(esp_real)
    if esp is None:
        return None

    if esp > Decimal("60"):
        return esp + MARGEM_LARGURA_ACIMA_60_MM

    alvo = esp + MARGEM_MINIMA_ESPESSURA_MM
    for largura in LARGURAS_STANDARD_ORLA:
        if largura >= alvo:
            return largura

    return esp + MARGEM_LARGURA_ACIMA_60_MM


def preco_ml_orla(preco, unidade, largura_orla_mm) -> tuple[Decimal | None, str | None]:
    """Return (preco_ml, aviso) for an orla reference.

    - unit ML -> use the price directly;
    - unit M2 -> ``preco * largura_orla_mm / 1000``;
    - unit unknown/empty (with a price) -> (None, AVISO_UNIDADE_ORLA);
    - no price -> (None, None).
    """
    preco = normalizar_numero(preco)
    if preco is None:
        return None, None

    unid = (unidade or "").strip().upper()
    if unid in ("ML", "M", "MTL"):
        return preco, None

    if unid in ("M2", "M²", "M2.", "MTQ", "METRO2", "M^2"):
        largura = normalizar_numero(largura_orla_mm)
        if largura is None:
            # M2 price but no roll width (missing thickness) -> can't convert.
            return None, AVISO_ESPESSURA_ORLA
        return preco * (largura / Decimal("1000")), None

    return None, AVISO_UNIDADE_ORLA


def calcular_orlas_linha(
    codigo_orlas, comp_real, larg_real, qt_total
) -> tuple[Decimal | None, Decimal | None]:
    """Return (ml_orla_fina, ml_orla_grossa) for one cost line.

    C1/C2 use comp_real, L1/L2 use larg_real; each banded side adds the
    edge-bander margin (``MARGEM_ORLADORA_POR_LADO_MM``) before everything is
    multiplied by qt_total and converted from mm to ML (``mm / 1000``).

    - empty / invalid / ``0000`` code -> (0, 0);
    - missing real measure for a banded side -> (None, None) without raising;
    - qt_total None -> assume 1; qt_total 0 -> result 0.
    """
    digitos = digitos_orla(codigo_orlas)
    if digitos is None or all(digito == 0 for digito in digitos):
        return Decimal("0"), Decimal("0")

    comp = normalizar_numero(comp_real)
    larg = normalizar_numero(larg_real)

    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")

    c1, c2, l1, l2 = digitos
    lados = ((c1, comp), (c2, comp), (l1, larg), (l2, larg))

    mm_fina = Decimal("0")
    mm_grossa = Decimal("0")
    for tipo, medida in lados:
        if tipo == ORLA_FINA:
            if medida is None:
                return None, None
            mm_fina += medida + MARGEM_ORLADORA_POR_LADO_MM
        elif tipo == ORLA_GROSSA:
            if medida is None:
                return None, None
            mm_grossa += medida + MARGEM_ORLADORA_POR_LADO_MM

    ml_fina = (mm_fina * qt) / Decimal("1000")
    ml_grossa = (mm_grossa * qt) / Decimal("1000")
    return ml_fina, ml_grossa


def calcular_custo_orla(ml, preco_ml) -> Decimal | None:
    """Return ml * preco_ml (price already per linear metre).

    - ml is 0 -> cost 0 (no banding, no cost);
    - ml is None (not computed) -> None;
    - ml > 0 but no price -> None.
    """
    ml = normalizar_numero(ml)
    if ml is None:
        return None
    if ml == 0:
        return Decimal("0")

    preco_ml = normalizar_numero(preco_ml)
    if preco_ml is None:
        return None

    return ml * preco_ml


def somar_custo_orlas(*custos) -> Decimal | None:
    """Total of the orla costs, or None when any component is unresolved."""
    if any(custo is None for custo in custos):
        return None

    return sum(custos, Decimal("0"))


def calcular_orlas_detalhe(
    codigo_orlas,
    comp_real,
    larg_real,
    esp_real,
    qt_total,
    *,
    ref_fina=None,
    preco_fina=None,
    unidade_fina=None,
    ref_grossa=None,
    preco_grossa=None,
    unidade_grossa=None,
) -> ResultadoOrlas:
    """Full edge banding result for one line: ML, cost and per-side detail.

    ``preco_fina``/``preco_grossa`` are the orla raw-material net prices and
    ``unidade_fina``/``unidade_grossa`` their units (M2 or ML). The roll width is
    chosen from ``esp_real``; M2 prices are converted to per-ML. A unit that is
    not validated leaves the cost empty and produces ``aviso`` (only for orla
    types actually used).
    """
    largura = selecionar_largura_orla_mm(esp_real)
    ml_fina, ml_grossa = calcular_orlas_linha(codigo_orlas, comp_real, larg_real, qt_total)

    preco_ml_fina, aviso_fina = preco_ml_orla(preco_fina, unidade_fina, largura)
    preco_ml_grossa, aviso_grossa = preco_ml_orla(preco_grossa, unidade_grossa, largura)

    custo_fina = calcular_custo_orla(ml_fina, preco_ml_fina)
    custo_grossa = calcular_custo_orla(ml_grossa, preco_ml_grossa)
    custo_orlas = somar_custo_orlas(custo_fina, custo_grossa)

    aviso = None
    if ml_fina is not None and ml_fina > 0 and aviso_fina:
        aviso = aviso_fina
    elif ml_grossa is not None and ml_grossa > 0 and aviso_grossa:
        aviso = aviso_grossa

    lados = _detalhe_lados(
        codigo_orlas,
        comp_real,
        larg_real,
        qt_total,
        largura,
        ref_fina,
        preco_fina,
        preco_ml_fina,
        ref_grossa,
        preco_grossa,
        preco_ml_grossa,
    )

    return ResultadoOrlas(
        ml_orla_fina=ml_fina,
        ml_orla_grossa=ml_grossa,
        custo_orla_fina=custo_fina,
        custo_orla_grossa=custo_grossa,
        custo_orlas=custo_orlas,
        largura_orla_mm=largura,
        aviso=aviso,
        lados=lados,
    )


def _detalhe_lados(
    codigo_orlas,
    comp_real,
    larg_real,
    qt_total,
    largura,
    ref_fina,
    preco_fina,
    preco_ml_fina,
    ref_grossa,
    preco_grossa,
    preco_ml_grossa,
) -> tuple[LadoOrla, ...]:
    """Build the per-side edge banding detail (best-effort, never raises)."""
    digitos = digitos_orla(codigo_orlas)
    if digitos is None:
        return ()

    comp = normalizar_numero(comp_real)
    larg = normalizar_numero(larg_real)
    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")

    c1, c2, l1, l2 = digitos
    config = (
        ("comp_lado_1", c1, comp),
        ("comp_lado_2", c2, comp),
        ("larg_lado_1", l1, larg),
        ("larg_lado_2", l2, larg),
    )

    lados: list[LadoOrla] = []
    for nome, tipo, base in config:
        ref = preco = preco_ml = None
        if tipo == ORLA_FINA:
            ref, preco, preco_ml = ref_fina, preco_fina, preco_ml_fina
        elif tipo == ORLA_GROSSA:
            ref, preco, preco_ml = ref_grossa, preco_grossa, preco_ml_grossa

        com_margem = ml = custo = None
        if tipo in (ORLA_FINA, ORLA_GROSSA) and base is not None:
            com_margem = base + MARGEM_ORLADORA_POR_LADO_MM
            ml = (com_margem * qt) / Decimal("1000")
            custo = calcular_custo_orla(ml, preco_ml)

        lados.append(
            LadoOrla(
                nome=nome,
                tipo=tipo,
                medida_base_mm=base if tipo in (ORLA_FINA, ORLA_GROSSA) else None,
                medida_com_margem_mm=com_margem,
                ml=ml,
                referencia=ref,
                largura_orla_mm=largura if tipo in (ORLA_FINA, ORLA_GROSSA) else None,
                preco=preco,
                preco_ml=preco_ml,
                custo=custo,
            )
        )

    return tuple(lados)
