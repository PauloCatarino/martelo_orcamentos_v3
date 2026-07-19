"""Guided explanation of how one piece↔operation link is costed (phase G1).

Builds, from the combination (tipo de operação × regra × unidade tempo ×
natureza da peça), the ACTIVE cost formula in plain language with a numeric
mini-example, plus the list of fields that do NOT count for that combination
(with the reason). The classification and the example numbers reuse the same
domain helpers as the costing engine (``classificar_operacao`` /
``calcular_tempo_operacao`` / ``calcular_custo_por_minutos`` /
``calcular_comprimento_rasgo_ml``), so the guide can never diverge from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.custo_producao import (
    calcular_comprimento_rasgo_ml,
    calcular_custo_por_minutos,
    calcular_tempo_operacao,
)
from app.domain.medidas import normalizar_numero
from app.domain import metodo_calculo_types as metodo_types
from app.domain.peca_natureza_types import FERRAGEM
from app.domain.regra_operacao_types import RASGO_CNC
from app.domain.tempos_producao import classificar_operacao

# Field keys the dialogs map to their input widgets.
CAMPO_QUANTIDADE_BASE = "quantidade_base"
CAMPO_TEMPO_SETUP = "tempo_setup"
CAMPO_TEMPO_POR_UNIDADE = "tempo_por_unidade"
CAMPO_UNIDADE_TEMPO = "unidade_tempo"

# Costing modes of one operation link.
MODO_TARIFA = "TARIFA"
MODO_RASGO = "RASGO"
MODO_TEMPO = "TEMPO"
MODO_ESCALAO_AREA = "ESCALAO_AREA"
MODO_FURACAO = "FURACAO"
MODO_REVESTIMENTO = "REVESTIMENTO"
MODO_SEM_CUSTEIO = "SEM_CUSTEIO"

# Example values used only to make the mini-example concrete.
_EXEMPLO_QT = Decimal("10")
_EXEMPLO_AREA_M2 = Decimal("0.5")
_EXEMPLO_COMP_MM = Decimal("600")
_EXEMPLO_LARG_MM = Decimal("400")

_BUCKETS_TARIFA = ("corte", "orlagem", "cnc")

_FORMULAS_TARIFA = {
    "corte": "Custo = perímetro da peça (ML) × QT × €/ML da máquina "
    "+ QT × setup por peça.",
    "orlagem": "Custo = tarifa € por lado orlado (lado curto/longo conforme a "
    "medida) × QT + QT × setup por peça. Só contam os lados com dígito 1 ou 2 "
    "no código de orlas (fina/grossa muda o material, não a tarifa).",
    "cnc": "Custo = preço do escalão de área da máquina (conforme a área da "
    "peça) × QT.",
}

NOTA_TEMPOS_INFORMATIVOS = (
    "Os campos de tempo/quantidade NÃO alteram este custo; alimentam apenas os "
    "tempos de produção informativos."
)


@dataclass(frozen=True)
class GuiaOperacao:
    """Plain-language costing guide for one operation configuration."""

    modo: str
    titulo: str
    linhas: tuple[str, ...]
    campos_inativos: dict[str, str] = field(default_factory=dict)


def construir_guia_operacao(
    *,
    tipo_operacao: str | None,
    codigo: str | None,
    regra_calculo: str | None,
    unidade_tempo: str | None,
    quantidade_base: Decimal | None = None,
    tempo_setup_minutos: Decimal | None = None,
    tempo_por_unidade_minutos: Decimal | None = None,
    rasgo_qt_comp: int = 0,
    rasgo_qt_larg: int = 0,
    custo_hora: Decimal | None = None,
    preco_rasgo_ml: Decimal | None = None,
    natureza_peca: str | None = None,
    metodo_calculo: str | None = None,
    preco_furo: Decimal | None = None,
    preco_m2_face: Decimal | None = None,
) -> GuiaOperacao:
    """Return the active formula + inactive fields for one operation link.

    When ``metodo_calculo`` is set (new CNC model) it drives the guide
    directly; without it the legacy classification applies.
    """
    metodo = metodo_types.normalize_metodo_calculo(metodo_calculo)
    if metodo == metodo_types.RASGO or (
        metodo is None and _eh_rasgo(codigo, regra_calculo)
    ):
        return _guia_rasgo(rasgo_qt_comp, rasgo_qt_larg, preco_rasgo_ml)
    if metodo == metodo_types.FURACAO:
        return _guia_furacao(quantidade_base, preco_furo)
    if metodo == metodo_types.REVESTIMENTO:
        return _guia_revestimento(quantidade_base, preco_m2_face)
    if metodo == metodo_types.ESCALAO_AREA:
        return _guia_escalao_area(
            tempo_setup_minutos is not None
            or tempo_por_unidade_minutos is not None
        )
    if metodo == metodo_types.TEMPO:
        return _guia_tempo(
            "cnc",
            (natureza_peca or "").strip().upper() or None,
            unidade_tempo,
            quantidade_base,
            tempo_setup_minutos,
            tempo_por_unidade_minutos,
            custo_hora,
        )

    bucket = classificar_operacao(tipo_operacao, codigo)
    natureza = (natureza_peca or "").strip().upper() or None

    if bucket is None:
        return _guia_sem_custeio()

    if bucket in _BUCKETS_TARIFA and natureza != FERRAGEM:
        tempos_preenchidos = (
            tempo_setup_minutos is not None
            or tempo_por_unidade_minutos is not None
        )
        return _guia_tarifa(bucket, natureza, tempos_preenchidos)

    return _guia_tempo(
        bucket,
        natureza,
        unidade_tempo,
        quantidade_base,
        tempo_setup_minutos,
        tempo_por_unidade_minutos,
        custo_hora,
    )


def _eh_rasgo(codigo: str | None, regra_calculo: str | None) -> bool:
    """Mirror the costing service's CNC-groove detection."""
    return (
        (codigo or "").strip().upper() == "CNC_RASGO"
        or (regra_calculo or "").strip().upper() == RASGO_CNC
    )


def _guia_sem_custeio() -> GuiaOperacao:
    return GuiaOperacao(
        modo=MODO_SEM_CUSTEIO,
        titulo="Fora do custeio automático",
        linhas=(
            "Esta operação não entra no custeio: o tipo/código não corresponde "
            "a nenhuma etapa conhecida (corte, orlagem, CNC, montagem, manual, "
            "furação, colagem, embalamento, setup).",
            "Escolha um tipo de operação reconhecido para a operação contar "
            "para o custo.",
        ),
    )


def _guia_tarifa(
    bucket: str, natureza: str | None, tempos_preenchidos: bool = False
) -> GuiaOperacao:
    linhas = [
        _FORMULAS_TARIFA[bucket],
        "As tarifas vêm da máquina da operação (STD/SÉRIE conforme o item).",
        NOTA_TEMPOS_INFORMATIVOS,
    ]
    if tempos_preenchidos:
        # Reinforced warning (G4): the user DID fill times on a tariff-mode
        # operation — e.g. hinge-cup drilling configured on a panel piece.
        linhas.insert(
            0,
            "⚠️ ATENÇÃO: os tempos que preencheu NÃO entram no custo desta "
            "operação — numa peça de painel o custo vem da tarifa da máquina. "
            "Para custear estes tempos (ex.: furação de uma dobradiça), "
            "configure a operação na peça ou linha ValueSet de FERRAGEM.",
        )
    if natureza is None:
        linhas.append(
            "Nota: numa peça de FERRAGEM esta operação contaria por tempo: "
            "(setup + quantidade × tempo por unidade) / 60 × custo/hora."
        )
    return GuiaOperacao(
        modo=MODO_TARIFA,
        titulo=f"Custo automático por tarifa da máquina ({bucket})",
        linhas=tuple(linhas),
    )


def _guia_rasgo(
    rasgo_qt_comp: int, rasgo_qt_larg: int, preco_rasgo_ml: Decimal | None
) -> GuiaOperacao:
    linhas = [
        "ML por peça = n.º comprimentos × COMP + n.º larguras × LARG "
        "(comprimento geométrico; a ida e volta da fresa não duplica).",
        "Custo = ML por peça × QT × €/ML de rasgo da máquina.",
    ]

    ml = calcular_comprimento_rasgo_ml(
        _EXEMPLO_COMP_MM, _EXEMPLO_LARG_MM, rasgo_qt_comp, rasgo_qt_larg
    )
    if ml is not None:
        exemplo = (
            f"Ex. (COMP {_fmt(_EXEMPLO_COMP_MM)} mm, LARG "
            f"{_fmt(_EXEMPLO_LARG_MM)} mm): {rasgo_qt_comp} × COMP + "
            f"{rasgo_qt_larg} × LARG = {_fmt(ml)} ML por peça"
        )
        preco = normalizar_numero(preco_rasgo_ml)
        if preco is not None:
            custo = ml * _EXEMPLO_QT * preco
            exemplo += (
                f" → × QT {_fmt(_EXEMPLO_QT)} × {_fmt(preco)} €/ML = "
                f"{_fmt_euros(custo)}"
            )
        else:
            exemplo += " (máquina sem €/ML de rasgo definido)"
        linhas.append(exemplo)
    else:
        linhas.append(
            "Defina pelo menos um comprimento ou uma largura de rasgo para "
            "haver custo."
        )

    motivo = (
        "Não conta para o custo: o rasgo custeia pela geometria "
        "(n.º comprimentos/larguras × medidas da peça × €/ML da máquina)."
    )
    return GuiaOperacao(
        modo=MODO_RASGO,
        titulo="Rasgo CNC: custo pela geometria do rasgo",
        linhas=tuple(linhas),
        campos_inativos={
            CAMPO_QUANTIDADE_BASE: motivo,
            CAMPO_TEMPO_SETUP: motivo,
            CAMPO_TEMPO_POR_UNIDADE: motivo,
            CAMPO_UNIDADE_TEMPO: motivo,
        },
    )


def _guia_escalao_area(tempos_preenchidos: bool) -> GuiaOperacao:
    """Method-driven variant of the CNC tariff guide (area tiers)."""
    motivo = (
        "Não conta para o custo: o método 'Escalões de área' usa apenas a "
        "área da peça e a tabela de escalões da máquina."
    )
    linhas = [
        _FORMULAS_TARIFA["cnc"],
        "As tarifas vêm dos escalões de área da máquina (STD/SÉRIE conforme "
        "o item).",
    ]
    if tempos_preenchidos:
        linhas.insert(
            0,
            "⚠️ ATENÇÃO: os tempos que preencheu NÃO entram no custo deste "
            "método — para custear por minutos escolha o método 'Tempo'.",
        )
    return GuiaOperacao(
        modo=MODO_ESCALAO_AREA,
        titulo="Escalões de área: preço por peça pelo escalão da área",
        linhas=tuple(linhas),
        campos_inativos={
            CAMPO_QUANTIDADE_BASE: motivo,
            CAMPO_TEMPO_SETUP: motivo,
            CAMPO_TEMPO_POR_UNIDADE: motivo,
            CAMPO_UNIDADE_TEMPO: motivo,
        },
    )


def _guia_furacao(
    quantidade_base: Decimal | None, preco_furo: Decimal | None
) -> GuiaOperacao:
    """Guide for the FURACAO method: holes per unit × QT × €/furo."""
    linhas = [
        "Custo = n.º de furos por unidade × QT × €/furo da máquina.",
        "A 'Quantidade base' é o n.º de furos por unidade (ex.: dobradiça "
        "= 3 furos).",
    ]
    furos = normalizar_numero(quantidade_base)
    preco = normalizar_numero(preco_furo)
    if furos is not None and furos > 0:
        exemplo = f"Ex. (QT {_fmt(_EXEMPLO_QT)}): {_fmt(furos)} furos/un × {_fmt(_EXEMPLO_QT)}"
        if preco is not None:
            custo = furos * _EXEMPLO_QT * preco
            exemplo += f" × {_fmt(preco)} €/furo = {_fmt_euros(custo)}"
        else:
            exemplo += " (máquina sem €/furo definido → sem custo)"
        linhas.append(exemplo)
    else:
        linhas.append(
            "Indique o n.º de furos por unidade para a operação contar."
        )
    motivo = (
        "Não conta para o custo: o método 'Furação' custeia por furo, não "
        "por tempo."
    )
    return GuiaOperacao(
        modo=MODO_FURACAO,
        titulo="Furação: custo por furo da máquina",
        linhas=tuple(linhas),
        campos_inativos={
            CAMPO_TEMPO_SETUP: motivo,
            CAMPO_TEMPO_POR_UNIDADE: motivo,
            CAMPO_UNIDADE_TEMPO: motivo,
        },
    )


def _guia_revestimento(
    quantidade_base: Decimal | None, preco_m2_face: Decimal | None
) -> GuiaOperacao:
    """Guide for the REVESTIMENTO method: m² × faces × €/m² per face."""
    linhas = [
        "Custo = área da peça (m²) × n.º de faces × QT × €/m² por face da "
        "máquina.",
        "A 'Quantidade base' é o n.º de faces revestidas (1 ou 2; vazio "
        "conta 1).",
    ]
    faces = normalizar_numero(quantidade_base)
    if faces is None or faces <= 0:
        faces = Decimal("1")
    preco = normalizar_numero(preco_m2_face)
    exemplo = (
        f"Ex. (área {_fmt(_EXEMPLO_AREA_M2)} m², QT {_fmt(_EXEMPLO_QT)}): "
        f"{_fmt(_EXEMPLO_AREA_M2)} × {_fmt(faces)} face(s) × "
        f"{_fmt(_EXEMPLO_QT)}"
    )
    if preco is not None:
        custo = _EXEMPLO_AREA_M2 * faces * _EXEMPLO_QT * preco
        exemplo += f" × {_fmt(preco)} €/m² = {_fmt_euros(custo)}"
    else:
        exemplo += " (máquina sem €/m² por face definido → sem custo)"
    linhas.append(exemplo)
    motivo = (
        "Não conta para o custo: o revestimento custeia por m² e por face."
    )
    return GuiaOperacao(
        modo=MODO_REVESTIMENTO,
        titulo="Revestimento: custo por m² e por face",
        linhas=tuple(linhas),
        campos_inativos={
            CAMPO_TEMPO_SETUP: motivo,
            CAMPO_TEMPO_POR_UNIDADE: motivo,
            CAMPO_UNIDADE_TEMPO: motivo,
        },
    )


def _guia_tempo(
    bucket: str,
    natureza: str | None,
    unidade_tempo: str | None,
    quantidade_base: Decimal | None,
    tempo_setup_minutos: Decimal | None,
    tempo_por_unidade_minutos: Decimal | None,
    custo_hora: Decimal | None,
) -> GuiaOperacao:
    unidade = (unidade_tempo or "").strip().upper()
    campos_inativos: dict[str, str] = {}

    if unidade == "M2":
        formula = (
            "Tempo = setup + (área da peça em m² × QT) × tempo por unidade."
        )
        campos_inativos[CAMPO_QUANTIDADE_BASE] = (
            "Não conta com a unidade 'Por m2': a quantidade calculada é a área "
            "da peça × QT."
        )
    elif unidade == "HORA":
        formula = (
            "Tempo = setup + quantidade base (em HORAS) × 60. A quantidade "
            "base é a duração da operação."
        )
        campos_inativos[CAMPO_TEMPO_POR_UNIDADE] = (
            "Não conta com a unidade 'Por hora': o tempo é a quantidade base "
            "em horas × 60."
        )
    elif unidade in ("LOTE", "OPERACAO"):
        formula = (
            "Tempo = setup + quantidade base × tempo por unidade "
            "(fixo: NÃO multiplica pela QT de peças)."
        )
    else:  # PECA, UN, FURO, ML ou vazio -> por unidade × QT
        formula = (
            "Tempo = setup + (quantidade base × QT) × tempo por unidade "
            "(quantidade base vazia conta como 1)."
        )

    linhas = [formula, "Custo = tempo / 60 × custo/hora da máquina."]
    linhas.append(
        _exemplo_tempo(
            unidade,
            quantidade_base,
            tempo_setup_minutos,
            tempo_por_unidade_minutos,
            custo_hora,
        )
    )

    if bucket in _BUCKETS_TARIFA and natureza == FERRAGEM:
        linhas.append(
            "Peça de FERRAGEM: esta operação conta por tempo (não por tarifa "
            "de painel)."
        )
    if bucket == "setup" and natureza != FERRAGEM:
        linhas.append(
            "Nota: em peças de painel, uma operação SETUP conta só para os "
            "tempos informativos, não para o custo."
        )

    return GuiaOperacao(
        modo=MODO_TEMPO,
        titulo="Custo por tempo (setup + quantidade × tempo por unidade)",
        linhas=tuple(linhas),
        campos_inativos=campos_inativos,
    )


def _exemplo_tempo(
    unidade: str,
    quantidade_base: Decimal | None,
    tempo_setup_minutos: Decimal | None,
    tempo_por_unidade_minutos: Decimal | None,
    custo_hora: Decimal | None,
) -> str:
    """Numeric mini-example computed with the real engine helpers."""
    setup_min, variavel_min = calcular_tempo_operacao(
        unidade or None,
        quantidade_base,
        tempo_setup_minutos,
        tempo_por_unidade_minutos,
        _EXEMPLO_AREA_M2,
        _EXEMPLO_QT,
    )
    if setup_min is None and variavel_min is None:
        return (
            "Preencha os tempos (setup e/ou tempo por unidade) para a operação "
            "contar; sem tempos, é ignorada sem aviso."
        )

    contexto = f"Ex. (QT {_fmt(_EXEMPLO_QT)}"
    if unidade == "M2":
        contexto += f", área {_fmt(_EXEMPLO_AREA_M2)} m²"
    contexto += ")"

    total = (setup_min or Decimal("0")) + (variavel_min or Decimal("0"))
    texto = (
        f"{contexto}: tempo = {_fmt(setup_min or Decimal('0'))} + "
        f"{_fmt(variavel_min or Decimal('0'))} = {_fmt(total)} min"
    )

    custo = calcular_custo_por_minutos(total, custo_hora)
    if custo is not None:
        texto += (
            f" → {_fmt(total)} / 60 × {_fmt(normalizar_numero(custo_hora))} €/h"
            f" = {_fmt_euros(custo)}"
        )
    else:
        texto += " (máquina sem custo/hora definido → sem custo)"
    return texto


def _fmt(value: Decimal | None) -> str:
    """Trimmed pt-style decimal (comma separator) for the guide text."""
    if value is None:
        return ""
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        normalized = normalized.quantize(Decimal("1"))
    return format(normalized, "f").replace(".", ",")


def _fmt_euros(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f").replace(".", ",") + " €"
