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
MOTIVO_SEM_ESCALOES = "SEM_ESCALOES"


def selecionar_escalao_area(escaloes_ativos, area_m2):
    """Return the area tier that applies to ``area_m2`` (or None).

    ``escaloes_ativos`` must already be active and ordered by ``nivel``. The first
    tier whose ``area_max_m2`` is None (no limit) or >= the area wins. Returns None
    when the area exceeds every finite tier and there is no no-limit tier.
    """
    area = normalizar_numero(area_m2)
    if area is None:
        return None

    for escalao in escaloes_ativos:
        limite = normalizar_numero(getattr(escalao, "area_max_m2", None))
        if limite is None or area <= limite:
            return escalao

    return None


def calcular_custo_cnc(
    area_m2,
    qt_total,
    escaloes_ativos,
) -> tuple[Decimal | None, str | None]:
    """Return (custo_cnc, motivo) priced by the machine's area tier.

    ``custo = preco_peca_std(escalão) * qt_total``. No active tiers / no matching
    tier / tier without price -> (None, SEM_ESCALOES). Missing area -> (None,
    SEM_DADOS) and the caller must NOT duplicate the dimensions warning. Never
    raises.
    """
    if not escaloes_ativos:
        return None, MOTIVO_SEM_ESCALOES

    area = normalizar_numero(area_m2)
    if area is None:
        return None, MOTIVO_SEM_DADOS

    escalao = selecionar_escalao_area(escaloes_ativos, area)
    if escalao is None:
        return None, MOTIVO_SEM_ESCALOES

    preco = normalizar_numero(getattr(escalao, "preco_peca_std", None))
    if preco is None:
        return None, MOTIVO_SEM_ESCALOES

    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")

    return preco * qt, None


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


_UNIDADES_TEMPO_M2 = ("M2",)
_UNIDADES_TEMPO_HORA = ("HORA",)
_UNIDADES_TEMPO_LOTE = ("LOTE", "OPERACAO")


def calcular_tempo_operacao(
    unidade_tempo,
    quantidade_base,
    tempo_setup_minutos,
    tempo_por_unidade_minutos,
    area_m2,
    qt_total,
) -> tuple[Decimal | None, Decimal | None]:
    """Return (setup_min, variavel_min) of an assembly/manual operation.

    tempo = setup + quantidade_calculada × tempo_por_unidade, with the calculated
    quantity per ``unidade_tempo``: PECA/UN/FURO/ML -> base × qt_total (base empty
    -> qt_total); M2 -> area_m2 × qt_total; HORA -> base hours × 60 (the operation
    time itself); LOTE/OPERACAO -> base or 1. Returns (None, None) when the
    operation has no time configured (so the caller ignores it without a warning).
    Never raises.
    """
    setup = normalizar_numero(tempo_setup_minutos)
    por_unidade = normalizar_numero(tempo_por_unidade_minutos)
    base = normalizar_numero(quantidade_base)
    qt = normalizar_numero(qt_total)
    if qt is None:
        qt = Decimal("1")
    unid = (unidade_tempo or "").strip().upper()

    if unid in _UNIDADES_TEMPO_HORA:
        # quantidade_base is the time in hours -> minutes (the operation time).
        if base is None and setup is None:
            return None, None
        return (setup or Decimal("0")), (base or Decimal("0")) * Decimal("60")

    if setup is None and por_unidade is None:
        return None, None

    por_unidade = por_unidade or Decimal("0")
    if unid in _UNIDADES_TEMPO_M2:
        quantidade_calculada = (normalizar_numero(area_m2) or Decimal("0")) * qt
    elif unid in _UNIDADES_TEMPO_LOTE:
        quantidade_calculada = base if base is not None else Decimal("1")
    else:  # PECA, UN, FURO, ML or empty -> per unit
        quantidade_calculada = (base if base is not None else Decimal("1")) * qt

    return (setup or Decimal("0")), quantidade_calculada * por_unidade


def calcular_custo_por_minutos(tempo_minutos, custo_hora_std) -> Decimal | None:
    """Return ``tempo × custo_hora_std / 60`` (€) or None when data is missing.

    Multiplies before dividing so clean inputs give exact results (no Decimal
    division artifacts).
    """
    tempo = normalizar_numero(tempo_minutos)
    custo_hora = normalizar_numero(custo_hora_std)
    if tempo is None or custo_hora is None:
        return None

    return (tempo * custo_hora) / Decimal("60")
