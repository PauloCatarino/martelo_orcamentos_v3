"""Industrial operation-line report for one budget version."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.medidas import normalizar_numero
from app.domain.regra_operacao_types import get_regra_operacao_label
from app.domain.tempos_producao import classificar_operacao
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.repositories.orcamento_item_repository import OrcamentoItemRepository
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)

ZERO = Decimal("0")
UM = Decimal("1")


@dataclass(frozen=True)
class RelatorioOperacaoLinha:
    item_ordem: int
    item: str
    linha_id: int
    linha: str
    tipo_linha: str
    operacao_ordem: int | None
    operacao: str
    tipo_operacao: str
    maquina: str
    origem: str
    acao: str
    regra: str
    quantidade_total: Decimal
    quantidade_base: Decimal | None
    setup_configurado_min: Decimal | None
    tempo_unidade_min: Decimal | None
    unidade_tempo: str
    tempo_atribuido_min: Decimal | None
    custo_atribuido: Decimal | None
    diagnostico: str


class RelatorioOperacoesService:
    """Build operation rows while preserving version-level production totals."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.item_repository = OrcamentoItemRepository(session)
        self.custeio_repository = OrcamentoItemCusteioLinhaRepository(session)
        self.linha_service = OrcamentoItemCusteioLinhaService(session)

    def listar_da_versao(
        self, orcamento_versao_id: int
    ) -> list[RelatorioOperacaoLinha]:
        items = self.item_repository.list_items_by_versao(orcamento_versao_id)
        items_by_id = {item.id: item for item in items}
        resultado: list[RelatorioOperacaoLinha] = []
        for linha in self.custeio_repository.list_by_orcamento_versao(
            orcamento_versao_id
        ):
            if not linha.ativo or linha.tipo_linha not in ("PECA", "FERRAGEM"):
                continue
            item = items_by_id.get(linha.orcamento_item_id)
            if item is None:
                continue
            fator_item = normalizar_numero(item.quantidade) or UM
            quantidade_total = (
                (normalizar_numero(linha.quantidade) or ZERO) * fator_item
            )
            operacoes = self.linha_service.listar_operacoes_efetivas_da_linha(
                linha.id
            )
            if not operacoes:
                resultado.append(
                    self._linha_sem_operacoes(
                        item, linha, quantidade_total
                    )
                )
                continue

            custos = self._custos_atribuidos(linha, operacoes, fator_item)
            tempos = self._tempos_atribuidos(linha, operacoes, fator_item)
            for indice, operacao in enumerate(operacoes):
                resultado.append(
                    RelatorioOperacaoLinha(
                        item_ordem=item.ordem,
                        item=(item.codigo or item.item or "").strip(),
                        linha_id=linha.id,
                        linha=(
                            linha.codigo
                            or linha.def_peca_codigo
                            or linha.descricao
                            or ""
                        ).strip(),
                        tipo_linha=linha.tipo_linha,
                        operacao_ordem=operacao.ordem,
                        operacao=" — ".join(
                            filter(None, (operacao.codigo, operacao.nome))
                        ),
                        tipo_operacao=operacao.tipo_operacao or "",
                        maquina=operacao.maquina or "—",
                        origem=operacao.origem,
                        acao=operacao.acao or "Base",
                        regra=get_regra_operacao_label(operacao.regra_calculo),
                        quantidade_total=quantidade_total,
                        quantidade_base=operacao.quantidade_base,
                        setup_configurado_min=operacao.tempo_setup_minutos,
                        tempo_unidade_min=operacao.tempo_por_unidade_minutos,
                        unidade_tempo=operacao.unidade_tempo or "",
                        tempo_atribuido_min=tempos.get(indice),
                        custo_atribuido=custos.get(indice),
                        diagnostico="",
                    )
                )
        return sorted(
            resultado,
            key=lambda row: (
                row.item_ordem,
                row.linha_id,
                row.operacao_ordem or 0,
                row.operacao,
            ),
        )

    @staticmethod
    def _bucket(operacao) -> str | None:
        return classificar_operacao(
            operacao.tipo_operacao, operacao.codigo
        )

    @classmethod
    def _custos_atribuidos(cls, linha, operacoes, fator_item: Decimal) -> dict:
        por_bucket = {
            "corte": normalizar_numero(linha.custo_corte),
            "orlagem": normalizar_numero(linha.custo_orlagem),
            "cnc": normalizar_numero(linha.custo_cnc),
            "montagem": normalizar_numero(linha.custo_montagem_manual),
            "manual": normalizar_numero(linha.custo_montagem_manual),
        }
        total_parciais = sum(
            (valor or ZERO for chave, valor in por_bucket.items() if chave != "manual"),
            ZERO,
        )
        total_linha = normalizar_numero(linha.custo_producao)
        fator_producao = (
            total_linha / total_parciais
            if total_linha is not None and total_parciais > 0
            else UM
        )
        resultado: dict[int, Decimal | None] = {}
        usados: set[str] = set()
        for indice, operacao in enumerate(operacoes):
            bucket = cls._bucket(operacao)
            if bucket is None or bucket in usados:
                resultado[indice] = None
                continue
            usados.add(bucket)
            valor = por_bucket.get(bucket)
            resultado[indice] = (
                valor * fator_producao * fator_item if valor is not None else None
            )
        if total_linha is not None and not any(
            valor is not None for valor in resultado.values()
        ):
            resultado[0] = total_linha * fator_item
        return resultado

    @classmethod
    def _tempos_atribuidos(cls, linha, operacoes, fator_item: Decimal) -> dict:
        por_bucket = {
            "corte": normalizar_numero(linha.tempo_corte),
            "orlagem": normalizar_numero(linha.tempo_orlagem),
            "cnc": normalizar_numero(linha.tempo_cnc),
            "montagem": normalizar_numero(linha.tempo_montagem),
            "manual": normalizar_numero(linha.tempo_manual),
        }
        resultado: dict[int, Decimal | None] = {}
        usados: set[str] = set()
        for indice, operacao in enumerate(operacoes):
            bucket = cls._bucket(operacao)
            if bucket is None or bucket in usados:
                resultado[indice] = None
                continue
            usados.add(bucket)
            valor = por_bucket.get(bucket)
            resultado[indice] = valor * fator_item if valor is not None else None
        return resultado

    @staticmethod
    def _linha_sem_operacoes(item, linha, quantidade_total) -> RelatorioOperacaoLinha:
        return RelatorioOperacaoLinha(
            item_ordem=item.ordem,
            item=(item.codigo or item.item or "").strip(),
            linha_id=linha.id,
            linha=(linha.codigo or linha.def_peca_codigo or linha.descricao or "").strip(),
            tipo_linha=linha.tipo_linha,
            operacao_ordem=None,
            operacao="(sem operações)",
            tipo_operacao="",
            maquina="—",
            origem="—",
            acao="—",
            regra="—",
            quantidade_total=quantidade_total,
            quantidade_base=None,
            setup_configurado_min=None,
            tempo_unidade_min=None,
            unidade_tempo="",
            tempo_atribuido_min=None,
            custo_atribuido=None,
            diagnostico="Confirmar se o custo de produção está completo.",
        )
