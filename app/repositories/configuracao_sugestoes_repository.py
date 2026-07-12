"""Reads for the "Copiar configuração de X" suggestions (phase G4).

Loads every ACTIVE existing configuration from the two catalog-level sources:
operations linked to piece definitions (``DefPecaOperacao``) and operations of
ValueSet model lines (``DefValuesetModeloLinhaOperacao``); associated
components come from ``DefPecaComponente``. Budget/item-level variant
operations are per-budget copies and are intentionally not used as sources.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.configuracao_sugestoes import (
    ORIGEM_MODELO_LINHA,
    ORIGEM_PECA,
    ConfigAssociadoExistente,
    ConfigOperacaoExistente,
)
from app.models import (
    DefPeca,
    DefPecaComponente,
    DefPecaOperacao,
    DefRegraQuantidade,
    DefValuesetModelo,
    DefValuesetModeloLinha,
    DefValuesetModeloLinhaOperacao,
)


def listar_configuracoes_operacao(session: Session) -> list[ConfigOperacaoExistente]:
    """List every active operation configuration from pieces and model lines."""
    configs: list[ConfigOperacaoExistente] = []

    statement = (
        select(DefPecaOperacao, DefPeca.codigo, DefPeca.nome)
        .join(DefPeca, DefPecaOperacao.def_peca_id == DefPeca.id)
        .where(
            DefPecaOperacao.ativo.is_(True),
            DefPeca.ativo.is_(True),
        )
        .order_by(DefPecaOperacao.id.asc())
    )
    for ligacao, peca_codigo, peca_nome in session.execute(statement):
        configs.append(
            ConfigOperacaoExistente(
                origem_tipo=ORIGEM_PECA,
                origem_id=ligacao.def_peca_id,
                origem_label=f"Peça {peca_codigo} - {peca_nome}",
                def_operacao_id=ligacao.def_operacao_id,
                regra_calculo=ligacao.regra_calculo,
                quantidade_base=ligacao.quantidade_base,
                rasgo_qt_comp=ligacao.rasgo_qt_comp,
                rasgo_qt_larg=ligacao.rasgo_qt_larg,
                tempo_setup_minutos=ligacao.tempo_setup_minutos,
                tempo_por_unidade_minutos=ligacao.tempo_por_unidade_minutos,
                unidade_tempo=ligacao.unidade_tempo,
                atualizado_em=ligacao.updated_at,
            )
        )

    statement = (
        select(
            DefValuesetModeloLinhaOperacao,
            DefValuesetModeloLinha,
            DefValuesetModelo.codigo,
        )
        .join(
            DefValuesetModeloLinha,
            DefValuesetModeloLinhaOperacao.def_valueset_modelo_linha_id
            == DefValuesetModeloLinha.id,
        )
        .join(
            DefValuesetModelo,
            DefValuesetModeloLinha.def_valueset_modelo_id == DefValuesetModelo.id,
        )
        .where(
            DefValuesetModeloLinhaOperacao.ativo.is_(True),
            DefValuesetModeloLinha.ativo.is_(True),
            DefValuesetModelo.ativo.is_(True),
        )
        .order_by(DefValuesetModeloLinhaOperacao.id.asc())
    )
    for ligacao, linha, modelo_codigo in session.execute(statement):
        opcao = linha.codigo_opcao or linha.nome_opcao or f"opção #{linha.id}"
        configs.append(
            ConfigOperacaoExistente(
                origem_tipo=ORIGEM_MODELO_LINHA,
                origem_id=linha.id,
                origem_label=f"Modelo {modelo_codigo} › {linha.chave}: {opcao}",
                def_operacao_id=ligacao.def_operacao_id,
                regra_calculo=ligacao.regra_calculo,
                quantidade_base=ligacao.quantidade_base,
                rasgo_qt_comp=ligacao.rasgo_qt_comp,
                rasgo_qt_larg=ligacao.rasgo_qt_larg,
                tempo_setup_minutos=ligacao.tempo_setup_minutos,
                tempo_por_unidade_minutos=ligacao.tempo_por_unidade_minutos,
                unidade_tempo=ligacao.unidade_tempo,
                atualizado_em=ligacao.updated_at,
            )
        )

    return configs


def listar_configuracoes_associado(session: Session) -> list[ConfigAssociadoExistente]:
    """List every active associated-component configuration with its parent piece."""
    statement = (
        select(
            DefPecaComponente,
            DefPeca.codigo,
            DefPeca.nome,
            DefRegraQuantidade.codigo,
        )
        .join(DefPeca, DefPecaComponente.def_peca_pai_id == DefPeca.id)
        .outerjoin(
            DefRegraQuantidade,
            DefPecaComponente.def_regra_quantidade_id == DefRegraQuantidade.id,
        )
        .where(
            DefPecaComponente.ativo.is_(True),
            DefPeca.ativo.is_(True),
        )
        .order_by(DefPecaComponente.id.asc())
    )

    configs: list[ConfigAssociadoExistente] = []
    for componente, pai_codigo, pai_nome, regra_codigo in session.execute(statement):
        configs.append(
            ConfigAssociadoExistente(
                origem_id=componente.id,
                def_peca_pai_id=componente.def_peca_pai_id,
                origem_label=f"Peça {pai_codigo} - {pai_nome}",
                tipo_componente=componente.tipo_componente,
                def_peca_componente_id=componente.def_peca_componente_id,
                referencia_componente=componente.referencia_componente,
                quantidade=componente.quantidade,
                def_regra_quantidade_id=componente.def_regra_quantidade_id,
                def_regra_quantidade_codigo=regra_codigo,
                zona_aplicacao=componente.zona_aplicacao,
                dimensao_referencia=componente.dimensao_referencia,
                numero_topos=componente.numero_topos,
                modo_quantidade=componente.modo_quantidade,
                formula_comp=componente.formula_comp,
                formula_larg=componente.formula_larg,
                formula_esp=componente.formula_esp,
                regra_quantidade=componente.regra_quantidade,
                atualizado_em=componente.updated_at,
            )
        )

    return configs
