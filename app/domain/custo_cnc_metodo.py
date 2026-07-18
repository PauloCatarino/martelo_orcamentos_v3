"""Method-driven CNC/coating cost dispatcher (pure, no I/O).

One CNC operation link is costed by its ``metodo_calculo`` — area tiers,
time, drilling, groove or coating — against the tariffs of the machine that
operation belongs to. The dispatcher delegates to the pure helpers in
``custo_producao`` so every method keeps a single formula shared with the
guide and the simulator. Tariffs (except area tiers) arrive already chosen
STD/SÉRIE by the caller via ``escolher_tarifa``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.custo_producao import (
    MOTIVO_MAQUINA_INCOMPATIVEL,
    MOTIVO_SEM_DADOS,
    calcular_custo_cnc,
    calcular_custo_furacao,
    calcular_custo_por_minutos,
    calcular_custo_rasgo_cnc,
    calcular_custo_revestimento_faces,
    calcular_tempo_operacao,
)
from app.domain.custo_producao import MOTIVO_SEM_TARIFA
from app.domain.medidas import normalizar_numero
from app.domain import metodo_calculo_types as metodo_types


@dataclass(frozen=True)
class TarifasCncMaquina:
    """Tariffs + capabilities of one CNC/coating machine, ready to price.

    ``preco_rasgo_ml``, ``preco_furo``, ``custo_hora`` and ``preco_m2_face``
    are the STD or SÉRIE values already selected by the caller; the area tiers
    keep both prices so the tier helper applies the SÉRIE→STD fallback itself.
    """

    escaloes_ativos: tuple = field(default_factory=tuple)
    preco_rasgo_ml: Decimal | None = None
    preco_furo: Decimal | None = None
    custo_hora: Decimal | None = None
    preco_m2_face: Decimal | None = None
    permite_escaloes_area: bool = True
    permite_rasgos: bool = True
    permite_furacao: bool = True


def calcular_custo_cnc_por_metodo(
    *,
    metodo: str | None,
    area_m2,
    comp_real,
    larg_real,
    qt_total,
    quantidade_base,
    rasgo_qt_comp,
    rasgo_qt_larg,
    tempo_setup_minutos,
    tempo_por_unidade_minutos,
    unidade_tempo,
    tarifas: TarifasCncMaquina,
    usar_serie: bool = False,
) -> tuple[Decimal | None, Decimal | None, str | None]:
    """Return (custo, tempo_minutos, motivo) for one method-driven link.

    ``tempo_minutos`` is only filled by the TEMPO method (it feeds the CNC
    time column); every other method prices without a time. A method the
    machine does not allow -> (None, None, MAQUINA_INCOMPATIVEL). Unknown or
    missing method -> (None, None, SEM_DADOS): the caller must resolve legacy
    rows with ``inferir_metodo_calculo_legado`` before dispatching. Never
    raises.
    """
    normalizado = metodo_types.normalize_metodo_calculo(metodo)
    if normalizado is None:
        return None, None, MOTIVO_SEM_DADOS

    if normalizado == metodo_types.ESCALAO_AREA:
        if not tarifas.permite_escaloes_area:
            return None, None, MOTIVO_MAQUINA_INCOMPATIVEL
        custo, motivo = calcular_custo_cnc(
            area_m2, qt_total, tarifas.escaloes_ativos, usar_serie=usar_serie
        )
        return custo, None, motivo

    if normalizado == metodo_types.TEMPO:
        setup_min, variavel_min = calcular_tempo_operacao(
            unidade_tempo,
            quantidade_base,
            tempo_setup_minutos,
            tempo_por_unidade_minutos,
            area_m2,
            qt_total,
        )
        if setup_min is None and variavel_min is None:
            return None, None, MOTIVO_SEM_DADOS
        total_min = (setup_min or Decimal("0")) + (variavel_min or Decimal("0"))
        custo = calcular_custo_por_minutos(total_min, tarifas.custo_hora)
        if custo is None:
            return None, total_min, MOTIVO_SEM_TARIFA
        return custo, total_min, None

    if normalizado == metodo_types.FURACAO:
        custo, motivo = calcular_custo_furacao(
            quantidade_base, qt_total, tarifas.preco_furo, tarifas.permite_furacao
        )
        return custo, None, motivo

    if normalizado == metodo_types.RASGO:
        custo, motivo = calcular_custo_rasgo_cnc(
            comp_real,
            larg_real,
            qt_total,
            rasgo_qt_comp,
            rasgo_qt_larg,
            tarifas.preco_rasgo_ml,
            tarifas.permite_rasgos,
        )
        return custo, None, motivo

    # REVESTIMENTO: quantidade_base is the number of coated faces (default 1).
    faces = normalizar_numero(quantidade_base)
    if faces is None or faces <= 0:
        faces = Decimal("1")
    custo, motivo = calcular_custo_revestimento_faces(
        area_m2, faces, qt_total, tarifas.preco_m2_face
    )
    return custo, None, motivo
