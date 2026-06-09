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

AVISO_MP_DADOS_INCOMPLETOS = "Custo MP não calculado: área ou preço em falta."
AVISO_FERRAGEM_DADOS_INCOMPLETOS = (
    "Custo ferragem não calculado: quantidade ou preço em falta."
)
AVISO_ML_DADOS_INCOMPLETOS = "Custo ML não calculado: consumo ou preço em falta."
# Written once (by the MP recompute) only for lines whose unit none of the cost
# rules (M2/ML/UND) can handle.
AVISO_UNIDADE_INVALIDA = "Custo não calculado: unidade não validada."

_UNIDADES_M2 = ("M2", "M²", "M^2", "MTQ", "METRO2")
_UNIDADES_ML = ("ML", "M", "MTL")
_UNIDADES_UND = ("UND", "UN", "UNI", "UNID", "PC", "PCS", "UNIDADE")


def unidade_custo_valida(unidade) -> bool:
    """Return True when the unit is handled by one of the cost rules (M2/ML/UND)."""
    unid = (unidade or "").strip().upper()
    return unid in _UNIDADES_M2 or unid in _UNIDADES_ML or unid in _UNIDADES_UND


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
    """Return (custo_mp, aviso) for one line. Only M2 is costed here.

    M2: ``area_m2 * qt_total * preco_liquido * (1 + desperdicio)``. ML / UND /
    unknown units are NOT MP's concern -> (None, None) with no warning (UND/ML are
    costed as Custo ferragem; the unit-invalid diagnostic is written elsewhere).
    Missing area or price (with M2): no cost + warning. Never raises.
    """
    unid = (unidade or "").strip().upper()

    if unid not in _UNIDADES_M2:
        return None, None

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
    Non-UND units -> (None, None) with no warning: M2 is handled by Custo MP, ML
    by calcular_custo_ml, and the unit-invalid diagnostic is written elsewhere.
    Missing quantity or price (with UND) -> no cost + warning.
    """
    unid = (unidade or "").strip().upper()

    if unid not in _UNIDADES_UND:
        return None, None

    qt = normalizar_numero(qt_total)
    preco = normalizar_numero(preco_liquido)
    if qt is None or preco is None:
        return None, AVISO_FERRAGEM_DADOS_INCOMPLETOS

    custo = qt * preco * fator_desperdicio(desperdicio_percentagem)
    return custo, None


def calcular_custo_acabamento_face(
    area_acabamento,
    preco_liquido,
    desperdicio_percentagem,
) -> Decimal | None:
    """Return the finishing cost of one face: ``area * preco * (1 + desp)``.

    None when the area or price is missing (caller decides the warning). The
    waste % is a small safety coefficient, normalized like the other costs.
    """
    area = normalizar_numero(area_acabamento)
    preco = normalizar_numero(preco_liquido)
    if area is None or preco is None:
        return None

    return area * preco * fator_desperdicio(desperdicio_percentagem)


def calcular_custo_total_linha(
    *,
    custo_mp=None,
    custo_orlas=None,
    custo_ferragem=None,
    custo_acabamento=None,
    custo_producao=None,
    excluir_mp: bool = False,
    excluir_orla: bool = False,
    excluir_ferragem: bool = False,
    excluir_acabamento: bool = False,
    excluir_producao: bool = False,
) -> Decimal:
    """Sum the partial costs of one line, honouring the exclusion flags.

    A True ``excluir_*`` flag means the matching cost is NOT summed. Missing /
    not-yet-implemented partial costs count as 0. Never raises.
    """
    total = Decimal("0")
    parcelas = (
        (excluir_mp, custo_mp),
        (excluir_orla, custo_orlas),
        (excluir_ferragem, custo_ferragem),
        (excluir_acabamento, custo_acabamento),
        (excluir_producao, custo_producao),
    )
    for excluido, custo in parcelas:
        if excluido:
            continue
        valor = normalizar_numero(custo)
        if valor is not None:
            total += valor

    return total


def calcular_custo_ml(
    unidade,
    consumo_ml_unitario,
    comp_real,
    larg_real,
    qt_total,
    preco_liquido,
    desperdicio_percentagem,
) -> tuple[bool, Decimal | None, Decimal | None, Decimal | None, str | None]:
    """Return (eh_ml, consumo_unitario, consumo_total, custo_ferragem, aviso).

    Only ML units are costed here (``eh_ml`` is False otherwise, so the caller
    leaves the line untouched). Linear-metre consumption per unit comes from the
    manual ``consumo_ml_unitario`` if set, else ``comp_real / 1000``, else
    ``larg_real / 1000``. The cost (stored in custo_ferragem) is
    ``consumo_ml_total * preco_liquido * (1 + desp)``. Never raises.
    """
    unid = (unidade or "").strip().upper()
    if unid not in _UNIDADES_ML:
        return False, None, None, None, None

    cmu = normalizar_numero(consumo_ml_unitario)
    if cmu is None:
        comp = normalizar_numero(comp_real)
        larg = normalizar_numero(larg_real)
        if comp is not None:
            cmu = comp / Decimal("1000")
        elif larg is not None:
            cmu = larg / Decimal("1000")

    if cmu is None:
        return True, None, None, None, AVISO_ML_DADOS_INCOMPLETOS

    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")
    consumo_total = cmu * qt

    preco = normalizar_numero(preco_liquido)
    if preco is None:
        return True, cmu, consumo_total, None, AVISO_ML_DADOS_INCOMPLETOS

    custo = consumo_total * preco * fator_desperdicio(desperdicio_percentagem)
    return True, cmu, consumo_total, custo, None
