"""Configuration recipes for operation and component dialogs (phase G3).

A recipe ("Configurar como…") fills the RIGHT fields for a common intent in
one step, so the user does not have to pick between 11 calculation rules and
9 time units by hand. The values are starting points aligned with the cost
model facts (the live guide shows the resulting formula immediately, and every
value stays editable).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.associado_types import (
    COMP,
    DOIS_TOPOS,
    GERAL,
    MEDIDA_TOPO,
    POR_TOPO,
    TOPO_1,
    TOTAL,
)
from app.domain.regra_operacao_types import FIXA, POR_FURACAO, POR_PECA, RASGO_CNC
from app.domain.regra_quantidade_types import FIXA as QUANTIDADE_FIXA

# Field keys of the operation dialog a recipe can fill.
CAMPO_REGRA_CALCULO = "regra_calculo"
CAMPO_QUANTIDADE_BASE = "quantidade_base"
CAMPO_TEMPO_SETUP = "tempo_setup"
CAMPO_TEMPO_POR_UNIDADE = "tempo_por_unidade"
CAMPO_UNIDADE_TEMPO = "unidade_tempo"
CAMPO_RASGO_QT_COMP = "rasgo_qt_comp"
CAMPO_RASGO_QT_LARG = "rasgo_qt_larg"

# Field keys of the component (associado) dialog a recipe can fill.
CAMPO_QUANTIDADE = "quantidade"
CAMPO_REGRA_QUANTIDADE = "regra_quantidade"
CAMPO_DEF_REGRA_QUANTIDADE = "def_regra_quantidade"
CAMPO_ZONA_APLICACAO = "zona_aplicacao"
CAMPO_DIMENSAO_REFERENCIA = "dimensao_referencia"
CAMPO_NUMERO_TOPOS = "numero_topos"
CAMPO_MODO_QUANTIDADE = "modo_quantidade"


@dataclass(frozen=True)
class Receita:
    """One 'Configurar como…' preset."""

    key: str
    label: str
    descricao: str
    valores: dict = field(default_factory=dict)
    # Field the user still has to review first (receives focus after applying).
    foco: str | None = None
    # When set, the recipe also selects the operation with this code (rasgo).
    operacao_codigo: str | None = None


RECEITAS_OPERACAO: tuple[Receita, ...] = (
    Receita(
        key="FERRAGEM_FURACAO_CNC",
        label="Ferragem com furação CNC (por furo)",
        descricao=(
            "Custo por tempo: n.º de furos × tempo por furo × QT, setup 1×. "
            "Ajuste o n.º de furos da ferragem (ex.: dobradiça = 4)."
        ),
        valores={
            CAMPO_REGRA_CALCULO: POR_FURACAO,
            CAMPO_UNIDADE_TEMPO: "FURO",
            CAMPO_QUANTIDADE_BASE: "4",
            CAMPO_TEMPO_SETUP: "0.5",
            CAMPO_TEMPO_POR_UNIDADE: "0.04",
        },
        foco=CAMPO_QUANTIDADE_BASE,
    ),
    Receita(
        key="POCKET_CNC_TEMPO",
        label="Cavidade/bolsa (pocket) CNC por tempo",
        descricao=(
            "Custo por tempo, 1 cavidade por peça × QT. Ajuste os minutos de "
            "maquinação da cavidade."
        ),
        valores={
            CAMPO_REGRA_CALCULO: FIXA,
            CAMPO_UNIDADE_TEMPO: "PECA",
            CAMPO_QUANTIDADE_BASE: "1",
            CAMPO_TEMPO_SETUP: "0.5",
            CAMPO_TEMPO_POR_UNIDADE: "1",
        },
        foco=CAMPO_TEMPO_POR_UNIDADE,
    ),
    Receita(
        key="MANUAL_POR_PECA",
        label="Operação manual/montagem por peça",
        descricao=(
            "Custo por tempo, multiplicado pela QT de peças. Ajuste os "
            "minutos por peça."
        ),
        valores={
            CAMPO_REGRA_CALCULO: POR_PECA,
            CAMPO_UNIDADE_TEMPO: "PECA",
            CAMPO_QUANTIDADE_BASE: "1",
            CAMPO_TEMPO_SETUP: "",
            CAMPO_TEMPO_POR_UNIDADE: "0.5",
        },
        foco=CAMPO_TEMPO_POR_UNIDADE,
    ),
    Receita(
        key="FIXO_POR_LOTE",
        label="Tempo fixo por lote/encomenda",
        descricao=(
            "Custo por tempo FIXO (não multiplica pela QT de peças) — ex.: "
            "preparação, afinação, embalamento do lote."
        ),
        valores={
            CAMPO_REGRA_CALCULO: FIXA,
            CAMPO_UNIDADE_TEMPO: "LOTE",
            CAMPO_QUANTIDADE_BASE: "1",
            CAMPO_TEMPO_SETUP: "",
            CAMPO_TEMPO_POR_UNIDADE: "5",
        },
        foco=CAMPO_TEMPO_POR_UNIDADE,
    ),
    Receita(
        key="RASGO_POR_COMPRIMENTO",
        label="Rasgo CNC por comprimento",
        descricao=(
            "Custo pela geometria: 1 rasgo ao comprimento × €/ML de rasgo da "
            "máquina. Ajuste o n.º de comprimentos/larguras."
        ),
        valores={
            CAMPO_REGRA_CALCULO: RASGO_CNC,
            CAMPO_RASGO_QT_COMP: 1,
            CAMPO_RASGO_QT_LARG: 0,
        },
        foco=CAMPO_RASGO_QT_COMP,
        operacao_codigo="CNC_RASGO",
    ),
)


RECEITAS_ASSOCIADO: tuple[Receita, ...] = (
    Receita(
        key="UNIAO_DOIS_TOPOS",
        label="União nos dois topos (cavilhas/parafusos)",
        descricao=(
            "Aplica nos DOIS topos da peça: quantidade por topo × 2, com a "
            "medida do topo disponível na regra (MEDIDA_TOPO). Escolha depois "
            "a regra de quantidade (ex.: por medida do topo)."
        ),
        valores={
            CAMPO_ZONA_APLICACAO: DOIS_TOPOS,
            CAMPO_MODO_QUANTIDADE: POR_TOPO,
            CAMPO_NUMERO_TOPOS: 2,
            CAMPO_DIMENSAO_REFERENCIA: MEDIDA_TOPO,
        },
        foco=CAMPO_DEF_REGRA_QUANTIDADE,
    ),
    Receita(
        key="UNIAO_UM_TOPO",
        label="União num topo",
        descricao=(
            "Aplica num só topo: quantidade por topo × 1, com a medida do "
            "topo disponível na regra (MEDIDA_TOPO)."
        ),
        valores={
            CAMPO_ZONA_APLICACAO: TOPO_1,
            CAMPO_MODO_QUANTIDADE: POR_TOPO,
            CAMPO_NUMERO_TOPOS: 1,
            CAMPO_DIMENSAO_REFERENCIA: MEDIDA_TOPO,
        },
        foco=CAMPO_DEF_REGRA_QUANTIDADE,
    ),
    Receita(
        key="SUPORTE_REGRA_MEDIDA",
        label="Suporte/ferragem com regra por medida",
        descricao=(
            "Quantidade total calculada por uma regra sobre o COMPRIMENTO da "
            "peça (ex.: 1 suporte a cada 800 mm). Escolha a regra de "
            "quantidade a seguir."
        ),
        valores={
            CAMPO_ZONA_APLICACAO: GERAL,
            CAMPO_MODO_QUANTIDADE: TOTAL,
            CAMPO_NUMERO_TOPOS: 0,
            CAMPO_DIMENSAO_REFERENCIA: COMP,
        },
        foco=CAMPO_DEF_REGRA_QUANTIDADE,
    ),
    Receita(
        key="ACESSORIO_FIXO",
        label="Acessório fixo por peça",
        descricao=(
            "Quantidade fixa (ex.: 1 fechadura por porta), sem regra nem "
            "topos."
        ),
        valores={
            CAMPO_QUANTIDADE: 1,
            CAMPO_REGRA_QUANTIDADE: QUANTIDADE_FIXA,
            CAMPO_DEF_REGRA_QUANTIDADE: None,
            CAMPO_ZONA_APLICACAO: GERAL,
            CAMPO_MODO_QUANTIDADE: TOTAL,
            CAMPO_NUMERO_TOPOS: 0,
            CAMPO_DIMENSAO_REFERENCIA: COMP,
        },
        foco=CAMPO_QUANTIDADE,
    ),
)


def get_receitas_operacao() -> tuple[Receita, ...]:
    """Return the operation dialog recipes."""
    return RECEITAS_OPERACAO


def get_receitas_associado() -> tuple[Receita, ...]:
    """Return the component (associado) dialog recipes."""
    return RECEITAS_ASSOCIADO
