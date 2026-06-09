"""Helpers for raw-material cost calculations on cost lines (phase 8I).

This phase only costs materials sold by square metre (M2), typically boards.
``area_m2`` is the unit area of one piece, so the quantity must be applied
explicitly. The waste percentage is applied here (unlike orlas, whose technical
waste is the +100 mm/side margin).
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.medidas import normalizar_numero
from app.domain.numeros import normalize_percentagem_humana

AVISO_MP_UNIDADE_ML = "Custo MP não calculado nesta fase: unidade ML."
AVISO_MP_UNIDADE_UND = "Custo MP não calculado nesta fase: unidade UND."
AVISO_MP_UNIDADE_INVALIDA = "Custo MP não calculado: unidade não validada."
AVISO_MP_DADOS_INCOMPLETOS = "Custo MP não calculado: área ou preço em falta."

AVISO_FERRAGEM_UNIDADE_ML = "Custo ferragem não calculado nesta fase: unidade ML."
AVISO_FERRAGEM_UNIDADE_INVALIDA = "Custo ferragem não calculado: unidade não validada."
AVISO_FERRAGEM_DADOS_INCOMPLETOS = (
    "Custo ferragem não calculado: quantidade ou preço em falta."
)

_UNIDADES_M2 = ("M2", "M²", "M^2", "MTQ", "METRO2")
_UNIDADES_ML = ("ML", "M", "MTL")
_UNIDADES_UND = ("UND", "UN", "UNI", "UNID", "PC", "PCS", "UNIDADE")


def desperdicio_para_fracao(desperdicio_percentagem) -> Decimal:
    """Normalize a waste value to a fraction (0.10 = 10%).

    Accepts a fraction (0.10) or a human percentage (10) and returns the
    fraction, never double-converting:
    None/empty -> 0; 0.10 -> 0.10; 10 -> 0.10; 100 -> 1.00.
    """
    humana = normalize_percentagem_humana(normalizar_numero(desperdicio_percentagem))
    if humana is None:
        return Decimal("0")

    return humana / Decimal("100")


def fator_desperdicio(desperdicio_percentagem) -> Decimal:
    """Return the waste multiplier (1 + fraction), accepting fraction or human %."""
    return Decimal("1") + desperdicio_para_fracao(desperdicio_percentagem)


def calcular_custo_mp(
    area_m2,
    qt_total,
    preco_liquido,
    desperdicio_percentagem,
    unidade,
) -> tuple[Decimal | None, str | None]:
    """Return (custo_mp, aviso) for one line. Only M2 is costed in this phase.

    M2: ``area_m2 * qt_total * preco_liquido * (1 + desperdicio)``.
    ML / UND / unknown unit: no cost + an explanatory warning.
    Missing area or price (with M2): no cost + warning. Never raises.
    """
    unid = (unidade or "").strip().upper()

    if unid in _UNIDADES_ML:
        return None, AVISO_MP_UNIDADE_ML
    if unid in _UNIDADES_UND:
        return None, AVISO_MP_UNIDADE_UND
    if unid not in _UNIDADES_M2:
        return None, AVISO_MP_UNIDADE_INVALIDA

    area = normalizar_numero(area_m2)
    preco = normalizar_numero(preco_liquido)
    if area is None or preco is None:
        return None, AVISO_MP_DADOS_INCOMPLETOS

    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")

    custo = area * qt * preco * fator_desperdicio(desperdicio_percentagem)
    return custo, None


def calcular_custo_ferragem(
    qt_total,
    preco_liquido,
    desperdicio_percentagem,
    unidade,
) -> tuple[Decimal | None, str | None]:
    """Return (custo_ferragem, aviso) for one line. Only UND is costed here.

    UND: ``qt_total * preco_liquido * (1 + desperdicio)`` — here the waste % is a
    technical safety coefficient (miscounts, damaged/lost parts), not material
    waste; orlas are intentionally excluded (they have their own +100 mm margin).
    M2 -> no cost, no warning (handled by Custo MP). ML / unknown unit -> no cost
    + warning. Missing quantity or price (with UND) -> no cost + warning.
    """
    unid = (unidade or "").strip().upper()

    if unid in _UNIDADES_M2:
        return None, None
    if unid in _UNIDADES_ML:
        return None, AVISO_FERRAGEM_UNIDADE_ML
    if unid not in _UNIDADES_UND:
        return None, AVISO_FERRAGEM_UNIDADE_INVALIDA

    qt = normalizar_numero(qt_total)
    preco = normalizar_numero(preco_liquido)
    if qt is None or preco is None:
        return None, AVISO_FERRAGEM_DADOS_INCOMPLETOS

    custo = qt * preco * fator_desperdicio(desperdicio_percentagem)
    return custo, None
