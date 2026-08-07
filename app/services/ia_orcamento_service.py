"""Memória privada e confirmação transacional das propostas de roupeiro."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.custeio_linha_types import DIVISAO_INDEPENDENTE
from app.domain.roupeiro_ia import AnaliseRoupeiro, PropostaComposicao, TIPO_ITEM_ROUPEIRO_ABRIR, ZonaDocumento
from app.models import (
    DefModulo,
    IaOrcamentoAnalise,
    IaOrcamentoProposta,
    IaOrcamentoPropostaModulo,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
)
from app.repositories.orcamento_item_modulo_repository import OrcamentoItemModuloRepository
from app.services.orcamento_item_custeio_linha_service import OrcamentoItemCusteioLinhaService
from app.services.orcamento_item_service import OrcamentoItemService


def _json_default(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    raise TypeError(type(valor).__name__)


class IaOrcamentoService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @staticmethod
    def hash_documento(caminho: str) -> str:
        ficheiro = Path(caminho)
        if not ficheiro.is_file():
            raise ValueError("O PDF selecionado não está acessível.")
        digest = hashlib.sha256()
        with ficheiro.open("rb") as stream:
            for bloco in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(bloco)
        return digest.hexdigest()

    def registar_analise_e_propostas(
        self,
        *,
        user_id: int,
        item_id: int,
        documento_path: str,
        pagina: int,
        zona: ZonaDocumento | None,
        fornecedor: str,
        modelo: str,
        analise: AnaliseRoupeiro,
        propostas: list[PropostaComposicao],
    ) -> tuple[int, list[int]]:
        item = self.session.get(OrcamentoItem, item_id)
        if item is None or item.tipo_item != TIPO_ITEM_ROUPEIRO_ABRIR:
            raise ValueError("O Assistente IA só pode ser usado num item Roupeiro Abrir.")
        row = IaOrcamentoAnalise(
            user_id=user_id,
            orcamento_item_id=item_id,
            documento_path=documento_path,
            documento_hash=self.hash_documento(documento_path),
            pagina=pagina,
            zona_json=json.dumps(asdict(zona), ensure_ascii=False) if zona else None,
            fornecedor=fornecedor,
            modelo=modelo,
            resultado_json=json.dumps(asdict(analise), ensure_ascii=False, default=_json_default),
        )
        self.session.add(row)
        self.session.flush()
        ids: list[int] = []
        for posicao, proposta in enumerate(propostas[:3], 1):
            proposta_row = IaOrcamentoProposta(
                analise_id=row.id,
                user_id=user_id,
                posicao_top3=posicao,
                pontuacao=proposta.pontuacao,
                explicacao=proposta.explicacao,
                proposta_original_json=json.dumps(asdict(proposta), ensure_ascii=False, default=_json_default),
            )
            self.session.add(proposta_row)
            self.session.flush()
            for componente in proposta.modulos:
                self.session.add(
                    IaOrcamentoPropostaModulo(
                        proposta_id=proposta_row.id,
                        def_modulo_id=componente.def_modulo_id,
                        ordem=componente.ordem,
                        codigo_snapshot=componente.codigo,
                        nome_snapshot=componente.nome,
                        largura_mm=componente.largura_mm,
                        espelhado=componente.espelhado,
                    )
                )
            ids.append(proposta_row.id)
        self.session.commit()
        return row.id, ids

    def bonus_privado_modulos(self, user_id: int) -> dict[int, float]:
        """Aprendizagem simples e privada: aceites sobem; rejeitados descem."""
        rows = self.session.execute(
            select(IaOrcamentoProposta.decisao, IaOrcamentoPropostaModulo.def_modulo_id)
            .join(IaOrcamentoPropostaModulo)
            .where(
                IaOrcamentoProposta.user_id == user_id,
                IaOrcamentoProposta.decisao.in_(("ACEITE", "REJEITADA")),
            )
        ).all()
        bonus: dict[int, float] = {}
        for decisao, modulo_id in rows:
            if modulo_id is None:
                continue
            bonus[modulo_id] = bonus.get(modulo_id, 0.0) + (1.0 if decisao == "ACEITE" else -0.2)
        return bonus

    def rejeitar(self, proposta_id: int, user_id: int, motivo: str | None = None) -> None:
        proposta = self._proposta_do_utilizador(proposta_id, user_id)
        proposta.decisao = "REJEITADA"
        proposta.motivo_rejeicao = (motivo or "").strip() or None
        self.session.commit()

    def corrigir_componentes(
        self,
        proposta_id: int,
        user_id: int,
        componentes: list[tuple[int, Decimal]],
    ) -> None:
        """Guarda trocas/larguras revistas sem tocar no orçamento."""
        proposta = self._proposta_do_utilizador(proposta_id, user_id)
        rows = self.session.execute(
            select(IaOrcamentoPropostaModulo)
            .where(IaOrcamentoPropostaModulo.proposta_id == proposta.id)
            .order_by(IaOrcamentoPropostaModulo.ordem)
        ).scalars().all()
        if not componentes:
            raise ValueError("A composição deve manter pelo menos um módulo.")
        if len(componentes) > len(rows):
            raise ValueError("A correção não pode acrescentar módulos nesta proposta.")
        correcoes = []
        for ordem, (row, (modulo_id, _largura_ignorada)) in enumerate(
            zip(rows, componentes), 1
        ):
            modulo = self.session.get(DefModulo, modulo_id)
            if modulo is None or not modulo.ativo:
                raise ValueError("Um dos módulos escolhidos já não está disponível.")
            row.ordem = ordem
            row.def_modulo_id = modulo.id
            row.codigo_snapshot = modulo.codigo
            row.nome_snapshot = modulo.nome
            row.largura_mm = Decimal("0")
            correcoes.append({"ordem": ordem, "modulo_id": modulo.id})
        removidos = rows[len(componentes):]
        for row in removidos:
            self.session.delete(row)
        if removidos:
            correcoes.append({"modulos_removidos": len(removidos)})
        proposta.correcoes_json = json.dumps(correcoes, ensure_ascii=False)
        self.session.commit()

    def confirmar(
        self,
        *,
        proposta_id: int,
        user_id: int,
        altura_mm: Decimal,
        largura_mm: Decimal,
        profundidade_mm: Decimal,
        correcoes: dict | None = None,
    ) -> list[int]:
        """Insere todos os módulos, estruturas e custeio numa única transação."""
        medidas = tuple(Decimal(str(v)) for v in (altura_mm, largura_mm, profundidade_mm))
        if any(valor <= 0 for valor in medidas):
            raise ValueError("Confirme altura, largura e profundidade com valores positivos.")
        proposta = self._proposta_do_utilizador(proposta_id, user_id)
        analise = self.session.get(IaOrcamentoAnalise, proposta.analise_id)
        if analise is None or analise.user_id != user_id:
            raise ValueError("Análise não encontrada para este utilizador.")
        item = self.session.get(OrcamentoItem, analise.orcamento_item_id)
        if item is None or item.tipo_item != TIPO_ITEM_ROUPEIRO_ABRIR:
            raise ValueError("O item deixou de ser um Roupeiro Abrir.")
        componentes = self.session.execute(
            select(IaOrcamentoPropostaModulo)
            .where(IaOrcamentoPropostaModulo.proposta_id == proposta.id)
            .order_by(IaOrcamentoPropostaModulo.ordem)
        ).scalars().all()
        if not componentes:
            raise ValueError("A proposta não tem módulos.")

        modulo_repo = OrcamentoItemModuloRepository(self.session)
        custeio = OrcamentoItemCusteioLinhaService(self.session)
        criados: list[int] = []
        commit_real = self.session.commit
        try:
            # O pipeline legado contém commits por etapa. Durante esta operação
            # eles tornam-se flushes; só o commit_real final pode tornar dados visíveis.
            self.session.commit = self.session.flush  # type: ignore[method-assign]
            item.altura, item.largura, item.profundidade = medidas
            analise.altura_confirmada_mm, analise.largura_confirmada_mm, analise.profundidade_confirmada_mm = medidas
            analise.estado = "CONFIRMADA"
            proposta.decisao = "ACEITE"
            proposta.correcoes_json = json.dumps(correcoes or {}, ensure_ascii=False, default=_json_default)
            for componente in componentes:
                if componente.def_modulo_id is None:
                    raise ValueError(f"O módulo {componente.codigo_snapshot} já não existe no catálogo.")
                modulo_item = modulo_repo.create_modulo(
                    orcamento_item_id=item.id,
                    ordem=modulo_repo.get_next_ordem(item.id),
                    nome=componente.nome_snapshot,
                    descricao="Inserido após confirmação do Assistente IA",
                    altura=medidas[0],
                    largura=None,
                    profundidade=medidas[2],
                    quantidade=Decimal("1"),
                    origem="IA",
                    def_modulo_id=componente.def_modulo_id,
                    ia_proposta_modulo_id=componente.id,
                    codigo_origem_snapshot=componente.codigo_snapshot,
                    nome_origem_snapshot=componente.nome_snapshot,
                )
                criados.append(modulo_item.id)
                custeio.inserir_modulo_no_item(
                    item.id,
                    componente.def_modulo_id,
                    orcamento_item_modulo_id=modulo_item.id,
                    commit=False,
                )
            custeio.recalcular_item_completo(item.id)
            OrcamentoItemService(self.session).recalcular_preco_item(item.id)
            self.session.flush()
            commit_real()
        except Exception:
            self.session.rollback()
            raise
        finally:
            self.session.commit = commit_real  # type: ignore[method-assign]
        return criados

    def _proposta_do_utilizador(self, proposta_id: int, user_id: int) -> IaOrcamentoProposta:
        proposta = self.session.get(IaOrcamentoProposta, proposta_id)
        if proposta is None or proposta.user_id != user_id:
            raise ValueError("Proposta não encontrada para este utilizador.")
        if proposta.decisao == "ACEITE":
            raise ValueError("Esta proposta já foi confirmada.")
        return proposta
