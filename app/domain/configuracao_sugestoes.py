"""Deterministic "Copiar configuração de X" suggestions (phase G4).

Given the configurations that ALREADY exist for the same operation (piece
links and ValueSet model line operations) or for the same associated
component (same component piece / reference on other parent pieces), build
ranked copy suggestions: identical configurations are grouped into one
suggestion, ranked by how often they are used and summarized in plain
language. No generative AI — the ranking is fully deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from app.domain.associado_types import (
    POR_TOPO,
    get_dimensao_referencia_options,
    get_modo_quantidade_options,
    get_zona_aplicacao_options,
)
from app.domain.operacao_receitas import (
    CAMPO_DEF_REGRA_QUANTIDADE,
    CAMPO_DIMENSAO_REFERENCIA,
    CAMPO_MODO_QUANTIDADE,
    CAMPO_NUMERO_TOPOS,
    CAMPO_QUANTIDADE,
    CAMPO_QUANTIDADE_BASE,
    CAMPO_RASGO_QT_COMP,
    CAMPO_RASGO_QT_LARG,
    CAMPO_REGRA_CALCULO,
    CAMPO_REGRA_QUANTIDADE,
    CAMPO_TEMPO_POR_UNIDADE,
    CAMPO_TEMPO_SETUP,
    CAMPO_UNIDADE_TEMPO,
    CAMPO_ZONA_APLICACAO,
)
from app.domain.regra_quantidade_types import normalize_regra_quantidade

# Extra field keys only used by the copy suggestions (child dimension formulas).
CAMPO_FORMULA_COMP = "formula_comp"
CAMPO_FORMULA_LARG = "formula_larg"
CAMPO_FORMULA_ESP = "formula_esp"

# Where an existing operation configuration lives.
ORIGEM_PECA = "PECA"
ORIGEM_MODELO_LINHA = "MODELO_LINHA"

_MAX_SUGESTOES = 5

_UNIDADE_RESUMO = {
    "PECA": "por peça",
    "ML": "por ML",
    "M2": "por m²",
    "FURO": "furo(s)",
    "UN": "unidade(s)",
    "HORA": "hora(s)",
    "OPERACAO": "por operação",
    "LOTE": "por lote",
}


@dataclass(frozen=True)
class ConfigOperacaoExistente:
    """One existing operation configuration usable as a copy source."""

    origem_tipo: str
    origem_id: int
    origem_label: str
    def_operacao_id: int
    regra_calculo: str | None
    quantidade_base: Decimal | None
    rasgo_qt_comp: int
    rasgo_qt_larg: int
    tempo_setup_minutos: Decimal | None
    tempo_por_unidade_minutos: Decimal | None
    unidade_tempo: str | None
    atualizado_em: datetime | None = None


@dataclass(frozen=True)
class ConfigAssociadoExistente:
    """One existing associated-component configuration usable as a copy source."""

    origem_id: int
    def_peca_pai_id: int
    origem_label: str
    tipo_componente: str
    def_peca_componente_id: int | None
    referencia_componente: str | None
    quantidade: Decimal
    def_regra_quantidade_id: int | None
    def_regra_quantidade_codigo: str | None
    zona_aplicacao: str
    dimensao_referencia: str
    numero_topos: int
    modo_quantidade: str
    formula_comp: str | None = None
    formula_larg: str | None = None
    formula_esp: str | None = None
    regra_quantidade: str | None = None
    atualizado_em: datetime | None = None


@dataclass(frozen=True)
class SugestaoConfiguracao:
    """One 'Copiar configuração de X' entry ready for the dialog combo."""

    label: str
    detalhe: str
    valores: dict = field(default_factory=dict)
    ocorrencias: int = 1


def construir_sugestoes_operacao(
    configs: list[ConfigOperacaoExistente],
    def_operacao_id: int | None,
    max_sugestoes: int = _MAX_SUGESTOES,
) -> list[SugestaoConfiguracao]:
    """Group and rank the existing configurations of one operation."""
    if def_operacao_id is None:
        return []

    candidatas = [
        config
        for config in configs
        if config.def_operacao_id == def_operacao_id
        and _operacao_tem_conteudo(config)
    ]
    grupos = _agrupar(candidatas, _chave_operacao)

    sugestoes = []
    for membros in grupos:
        exemplo = membros[0]
        resumo = _resumo_operacao(exemplo)
        sugestoes.append(
            SugestaoConfiguracao(
                label=f"{exemplo.origem_label} — {resumo}",
                detalhe=_detalhe(membros, resumo),
                valores={
                    CAMPO_REGRA_CALCULO: exemplo.regra_calculo,
                    CAMPO_QUANTIDADE_BASE: _texto(exemplo.quantidade_base),
                    CAMPO_TEMPO_SETUP: _texto(exemplo.tempo_setup_minutos),
                    CAMPO_TEMPO_POR_UNIDADE: _texto(
                        exemplo.tempo_por_unidade_minutos
                    ),
                    CAMPO_UNIDADE_TEMPO: _codigo(exemplo.unidade_tempo),
                    CAMPO_RASGO_QT_COMP: exemplo.rasgo_qt_comp,
                    CAMPO_RASGO_QT_LARG: exemplo.rasgo_qt_larg,
                },
                ocorrencias=len(membros),
            )
        )
    return sugestoes[:max_sugestoes]


def construir_sugestoes_associado(
    configs: list[ConfigAssociadoExistente],
    def_peca_componente_id: int | None = None,
    referencia_componente: str | None = None,
    max_sugestoes: int = _MAX_SUGESTOES,
) -> list[SugestaoConfiguracao]:
    """Group and rank existing configurations of the same component elsewhere."""
    referencia = (referencia_componente or "").strip().upper() or None
    if def_peca_componente_id is not None:
        candidatas = [
            config
            for config in configs
            if config.def_peca_componente_id == def_peca_componente_id
        ]
    elif referencia is not None:
        candidatas = [
            config
            for config in configs
            if (config.referencia_componente or "").strip().upper() == referencia
        ]
    else:
        return []

    grupos = _agrupar(candidatas, _chave_associado)

    sugestoes = []
    for membros in grupos:
        exemplo = membros[0]
        resumo = _resumo_associado(exemplo)
        sugestoes.append(
            SugestaoConfiguracao(
                label=f"{exemplo.origem_label} — {resumo}",
                detalhe=_detalhe(membros, resumo),
                valores={
                    CAMPO_QUANTIDADE: exemplo.quantidade,
                    CAMPO_REGRA_QUANTIDADE: normalize_regra_quantidade(
                        exemplo.regra_quantidade
                    ),
                    CAMPO_DEF_REGRA_QUANTIDADE: exemplo.def_regra_quantidade_id,
                    CAMPO_ZONA_APLICACAO: exemplo.zona_aplicacao,
                    CAMPO_DIMENSAO_REFERENCIA: exemplo.dimensao_referencia,
                    CAMPO_NUMERO_TOPOS: exemplo.numero_topos,
                    CAMPO_MODO_QUANTIDADE: exemplo.modo_quantidade,
                    CAMPO_FORMULA_COMP: exemplo.formula_comp or "",
                    CAMPO_FORMULA_LARG: exemplo.formula_larg or "",
                    CAMPO_FORMULA_ESP: exemplo.formula_esp or "",
                },
                ocorrencias=len(membros),
            )
        )
    return sugestoes[:max_sugestoes]


def _operacao_tem_conteudo(config: ConfigOperacaoExistente) -> bool:
    """Skip configurations with nothing worth copying (e.g. plain tariff ops)."""
    return (
        config.quantidade_base is not None
        or config.tempo_setup_minutos is not None
        or config.tempo_por_unidade_minutos is not None
        or _codigo(config.unidade_tempo) is not None
        or config.rasgo_qt_comp > 0
        or config.rasgo_qt_larg > 0
    )


def _agrupar(candidatas: list, chave) -> list[list]:
    """Group identical configurations and rank the groups deterministically."""
    grupos: dict[tuple, list] = {}
    for config in candidatas:
        grupos.setdefault(chave(config), []).append(config)

    def _ordem(membros: list) -> tuple:
        mais_recente = max(
            (m.atualizado_em for m in membros if m.atualizado_em is not None),
            default=datetime.min,
        )
        return (-len(membros), -mais_recente.timestamp() if mais_recente != datetime.min else 0.0,
                membros[0].origem_label)

    return sorted(grupos.values(), key=_ordem)


def _chave_operacao(config: ConfigOperacaoExistente) -> tuple:
    return (
        _codigo(config.regra_calculo),
        _num(config.quantidade_base),
        config.rasgo_qt_comp,
        config.rasgo_qt_larg,
        _num(config.tempo_setup_minutos),
        _num(config.tempo_por_unidade_minutos),
        _codigo(config.unidade_tempo),
    )


def _chave_associado(config: ConfigAssociadoExistente) -> tuple:
    return (
        _num(config.quantidade),
        normalize_regra_quantidade(config.regra_quantidade),
        config.def_regra_quantidade_id,
        _codigo(config.zona_aplicacao),
        _codigo(config.dimensao_referencia),
        config.numero_topos,
        _codigo(config.modo_quantidade),
        (config.formula_comp or "").strip(),
        (config.formula_larg or "").strip(),
        (config.formula_esp or "").strip(),
    )


def _resumo_operacao(config: ConfigOperacaoExistente) -> str:
    """Compact human summary, e.g. '4 furo(s) × 0,04 min, setup 0,5 min'."""
    if config.rasgo_qt_comp > 0 or config.rasgo_qt_larg > 0:
        return (
            f"rasgo {config.rasgo_qt_comp} × COMP + "
            f"{config.rasgo_qt_larg} × LARG"
        )

    partes = []
    unidade = _codigo(config.unidade_tempo)
    quantidade = _fmt(config.quantidade_base)
    tempo = _fmt(config.tempo_por_unidade_minutos)
    if quantidade and unidade in ("FURO", "UN"):
        base = f"{quantidade} {_UNIDADE_RESUMO[unidade]}"
    elif quantidade and unidade:
        base = f"{quantidade} × {_UNIDADE_RESUMO.get(unidade, unidade.lower())}"
    elif unidade:
        base = _UNIDADE_RESUMO.get(unidade, unidade.lower())
    else:
        base = f"quantidade {quantidade}" if quantidade else ""
    if base and tempo:
        partes.append(f"{base} × {tempo} min")
    elif base:
        partes.append(base)
    elif tempo:
        partes.append(f"{tempo} min por unidade")
    setup = _fmt(config.tempo_setup_minutos)
    if setup:
        partes.append(f"setup {setup} min")
    return ", ".join(partes) or "sem tempos"


def _resumo_associado(config: ConfigAssociadoExistente) -> str:
    """Compact human summary, e.g. 'regra CAV300, por topo × 2, Dois topos'."""
    partes = []
    if config.def_regra_quantidade_codigo:
        partes.append(f"regra {config.def_regra_quantidade_codigo}")
    else:
        partes.append(f"quantidade {_fmt(config.quantidade) or '1'}")
    if _codigo(config.modo_quantidade) == POR_TOPO:
        partes.append(f"por topo × {config.numero_topos}")
        partes.append(
            _label(get_dimensao_referencia_options(), config.dimensao_referencia)
        )
    else:
        partes.append(_label(get_zona_aplicacao_options(), config.zona_aplicacao))
    if config.formula_comp or config.formula_larg or config.formula_esp:
        partes.append("com fórmulas dimensionais")
    return ", ".join(parte for parte in partes if parte)


def _detalhe(membros: list, resumo: str) -> str:
    """Tooltip text: full summary plus every origin using this configuration."""
    origens = sorted({membro.origem_label for membro in membros})
    linhas = [resumo, ""]
    if len(origens) == 1:
        linhas.append(f"Usada em: {origens[0]}")
    else:
        linhas.append(f"Usada em {len(origens)} sítios:")
        linhas.extend(f"• {origem}" for origem in origens)
    return "\n".join(linhas)


def _label(options: tuple, code: str | None) -> str:
    return dict(options).get(_codigo(code), _codigo(code) or "")


def _codigo(value: str | None) -> str | None:
    normalized = (value or "").strip().upper()
    return normalized or None


def _num(value: Decimal | None) -> Decimal | None:
    return value.normalize() if value is not None else None


def _texto(value: Decimal | None) -> str:
    """Decimal → dialog text field value ('' when empty)."""
    return format(value.normalize(), "f") if value is not None else ""


def _fmt(value: Decimal | None) -> str:
    """Trimmed pt-style decimal for the summaries."""
    if value is None:
        return ""
    normalized = value.normalize()
    if normalized == normalized.to_integral_value():
        normalized = normalized.quantize(Decimal("1"))
    return format(normalized, "f").replace(".", ",")
