"""Cutting/edging production cost helpers from machine STD tariffs (phase 8S.1).

Cut cost uses the unit perimeter × quantity × €/ML (+ setup × quantity); edging
cost uses the line's total edging metres × €/ML (+ setup × quantity). The caller
only invokes these when the piece actually has the matching operation. SERIE
tariffs and CNC area tiers are handled in later phases.
"""

from __future__ import annotations

from decimal import Decimal

from app.domain.medidas import normalizar_numero

# Reasons returned to the caller, which formats the production observation.
MOTIVO_SEM_TARIFA = "SEM_TARIFA"
MOTIVO_SEM_DADOS = "SEM_DADOS"


def calcular_custo_corte(
    perimetro_ml,
    qt_total,
    preco_ml_std,
    custo_setup_peca_std,
) -> tuple[Decimal | None, str | None]:
    """Return (custo_corte, motivo).

    ``custo = perimetro_ml * qt_total * preco_ml_std + qt_total * setup``. Without
    the machine €/ML -> (None, SEM_TARIFA); without the perimeter -> (None,
    SEM_DADOS). Never raises.
    """
    preco = normalizar_numero(preco_ml_std)
    if preco is None:
        return None, MOTIVO_SEM_TARIFA

    perimetro = normalizar_numero(perimetro_ml)
    if perimetro is None:
        return None, MOTIVO_SEM_DADOS

    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")

    custo = perimetro * qt * preco
    setup = normalizar_numero(custo_setup_peca_std)
    if setup is not None:
        custo += qt * setup

    return custo, None


def calcular_custo_orlagem(
    ml_orla_total,
    qt_total,
    preco_ml_std,
    custo_setup_peca_std,
) -> tuple[Decimal | None, str | None]:
    """Return (custo_orlagem, motivo).

    ``ml_orla_total`` is already the line total (not multiplied by quantity).
    ``custo = ml_orla_total * preco_ml_std + qt_total * setup``. No edging
    (ml_orla_total <= 0) -> (0, None) with no setup and no warning. Without the
    machine €/ML (and there IS edging) -> (None, SEM_TARIFA). Never raises.
    """
    ml = normalizar_numero(ml_orla_total) or Decimal("0")
    if ml <= 0:
        return Decimal("0"), None

    preco = normalizar_numero(preco_ml_std)
    if preco is None:
        return None, MOTIVO_SEM_TARIFA

    custo = ml * preco
    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")
    setup = normalizar_numero(custo_setup_peca_std)
    if setup is not None:
        custo += qt * setup

    return custo, None


def somar_custo_producao(*parciais) -> Decimal | None:
    """Sum the production partials; empty ones count as 0, all-empty -> None."""
    presentes = [normalizar_numero(p) for p in parciais if p is not None]
    if not presentes:
        return None

    return sum(presentes, Decimal("0"))
