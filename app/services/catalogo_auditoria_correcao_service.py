"""Supervised, narrowly-scoped fixes for catalog audit findings."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    DefModuloLinha,
    DefOperacao,
    DefPecaComponente,
    DefPecaOperacao,
    DefRegraQuantidade,
)
from app.services.catalogo_auditoria_service import CatalogoAuditoriaItem


class CatalogoAuditoriaCorrecaoService:
    """Apply only corrections that can be revalidated immediately before write."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def aplicar(self, item: CatalogoAuditoriaItem) -> str:
        codigo = item.correcao_codigo
        if not codigo or item.correcao_alvo_id is None:
            raise ValueError("Esta ocorrência não tem correção automática segura.")

        if codigo == "DESATIVAR_LIGACAO_OPERACAO_INATIVA":
            mensagem = self._desativar_ligacao_operacao_inativa(
                item.correcao_alvo_id
            )
        elif codigo == "DESATIVAR_REGRA_NAO_UTILIZADA":
            mensagem = self._desativar_regra_nao_utilizada(item.correcao_alvo_id)
        elif codigo == "ATUALIZAR_CODIGO_PECA_MODULO":
            mensagem = self._atualizar_codigo_peca_modulo(item.correcao_alvo_id)
        else:
            raise ValueError("Tipo de correção automática não suportado.")

        self.session.commit()
        return mensagem

    def _desativar_ligacao_operacao_inativa(self, ligacao_id: int) -> str:
        ligacao = self.session.get(DefPecaOperacao, ligacao_id)
        if ligacao is None or not ligacao.ativo:
            raise ValueError("A ligação já não existe ou já está inativa.")
        operacao = self.session.get(DefOperacao, ligacao.def_operacao_id)
        if operacao is None:
            raise ValueError(
                "A operação já não existe; abra a peça para corrigir a ligação."
            )
        if operacao.ativo:
            raise ValueError(
                "A operação já está ativa; a correção proposta deixou de ser válida."
            )
        ligacao.ativo = False
        return "Ligação à operação inativa desativada na peça."

    def _desativar_regra_nao_utilizada(self, regra_id: int) -> str:
        regra = self.session.get(DefRegraQuantidade, regra_id)
        if regra is None or not regra.ativo:
            raise ValueError("A regra já não existe ou já está inativa.")

        componente = self.session.execute(
            select(DefPecaComponente.id).where(
                DefPecaComponente.def_regra_quantidade_id == regra_id,
                DefPecaComponente.ativo.is_(True),
            ).limit(1)
        ).scalar_one_or_none()
        modulo = self.session.execute(
            select(DefModuloLinha.id).where(
                DefModuloLinha.def_regra_quantidade_id == regra_id,
                DefModuloLinha.ativo.is_(True),
            ).limit(1)
        ).scalar_one_or_none()
        if componente is not None or modulo is not None:
            raise ValueError(
                "A regra passou a estar em utilização; a correção foi cancelada."
            )
        regra.ativo = False
        return "Regra sem utilização desativada; pode ser reativada nas configurações."

    def _atualizar_codigo_peca_modulo(self, linha_id: int) -> str:
        linha = self.session.get(DefModuloLinha, linha_id)
        if linha is None or not linha.ativo:
            raise ValueError("A linha de módulo já não existe ou está inativa.")
        if linha.def_peca_id is None:
            raise ValueError("A linha deixou de estar ligada a uma peça.")
        from app.models import DefPeca

        peca = self.session.get(DefPeca, linha.def_peca_id)
        if peca is None:
            raise ValueError("A peça ligada ao módulo já não existe.")
        if linha.def_peca_codigo == peca.codigo:
            raise ValueError("O código guardado já está atualizado.")
        anterior = linha.def_peca_codigo or "(vazio)"
        linha.def_peca_codigo = peca.codigo
        return f"Código da linha de módulo atualizado de {anterior} para {peca.codigo}."
