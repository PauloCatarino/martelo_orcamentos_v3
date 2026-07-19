"""Calculation-method constants for CNC/coating operation links.

The method lives on the piece↔operation link (def_peça, ValueSet line or local
costing operation) and drives HOW that link is costed. The machine declares
which methods it allows (capability flags + available tariffs); the dialogs
filter the method combo with ``metodos_disponiveis_para_maquina``. Legacy rows
without a stored method are resolved with ``inferir_metodo_calculo_legado``
(the same heuristic the Alembic backfill used).
"""

from __future__ import annotations

from app.domain.regra_operacao_types import POR_FURACAO, RASGO_CNC

ESCALAO_AREA = "ESCALAO_AREA"
TEMPO = "TEMPO"
POCKET = "POCKET"
FURACAO = "FURACAO"
RASGO = "RASGO"
REVESTIMENTO = "REVESTIMENTO"

METODO_CALCULO_LABELS = {
    ESCALAO_AREA: "Escalões de área (€/peça pelo escalão da área)",
    TEMPO: "Tempo (minutos × custo/hora da máquina)",
    POCKET: "Pocket (minutos × custo/hora da máquina)",
    FURACAO: "Furação (n.º furos × €/furo da máquina)",
    RASGO: "Rasgo (ML geométrico × €/ML da máquina)",
    REVESTIMENTO: "Revestimento (m² × n.º faces × €/m² da máquina)",
}


def get_metodo_calculo_label(metodo: str | None) -> str:
    """Return a friendly label for a calculation method ('' when empty)."""
    normalized = normalize_metodo_calculo(metodo)
    if normalized is None:
        return ""
    return METODO_CALCULO_LABELS[normalized]


def get_metodo_calculo_options() -> tuple[tuple[str, str], ...]:
    """Return method options as code/label pairs."""
    return tuple(METODO_CALCULO_LABELS.items())


def normalize_metodo_calculo(metodo: str | None) -> str | None:
    """Normalize a method code; unknown/empty -> None (legacy row)."""
    if not metodo:
        return None

    normalized = metodo.strip().upper()
    if normalized in METODO_CALCULO_LABELS:
        return normalized

    return None


def metodos_disponiveis_para_maquina(maquina) -> tuple[str, ...]:
    """Return the methods one machine allows (empty for non-CNC machines).

    A coating machine (tipo REVESTIMENTO) only coats; a CNC machine always
    allows TEMPO (its custo/hora) and adds the methods enabled by its
    capability flags. POCKET is a time-based CNC method exposed only when the
    machine enables ``permite_pocket``. Other machine types (corte, orlagem,
    montagem, manual) keep the legacy tariff/time costing and have no method
    to choose.
    """
    if maquina is None:
        return ()

    tipo = (getattr(maquina, "tipo", None) or "").strip().upper()
    if tipo == REVESTIMENTO:
        return (REVESTIMENTO,)
    if tipo != "CNC":
        return ()

    metodos: list[str] = []
    if getattr(maquina, "permite_escaloes_area", False):
        metodos.append(ESCALAO_AREA)
    metodos.append(TEMPO)
    if getattr(maquina, "permite_pocket", False):
        metodos.append(POCKET)
    if getattr(maquina, "permite_furacao", False):
        metodos.append(FURACAO)
    if getattr(maquina, "permite_rasgos", False):
        metodos.append(RASGO)
    return tuple(metodos)


def inferir_metodo_calculo_legado(
    codigo_operacao: str | None,
    regra_calculo: str | None,
    rasgo_qt_comp,
    rasgo_qt_larg,
    tem_tempos: bool,
) -> str:
    """Resolve the method of a legacy CNC link that has none stored.

    Mirrors the migration backfill: groove markers win, then the drilling
    rule, then filled times, and area tiers are the panel default.
    """
    codigo = (codigo_operacao or "").strip().upper()
    regra = (regra_calculo or "").strip().upper()
    if (
        codigo == "CNC_RASGO"
        or regra == RASGO_CNC
        or int(rasgo_qt_comp or 0) > 0
        or int(rasgo_qt_larg or 0) > 0
    ):
        return RASGO
    if regra == POR_FURACAO:
        return FURACAO
    if tem_tempos:
        return TEMPO
    return ESCALAO_AREA
