"""Service that aggregates the consumption/cost of a budget version (phase 8W.0).

Reads the ACTIVE cost lines of every item of the version, multiplies each line
by its item's quantity, and delegates the aggregation to the pure
``app.domain.consumos``. No UI here (the report page is phase 8W.1).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.consumos import LinhaConsumo, ResumoConsumos, agregar_consumos
from app.domain.precos import MargensOrcamento
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.repositories.orcamento_item_repository import OrcamentoItemRepository

_UM = Decimal("1")
_ZERO = Decimal("0")


class RelatorioConsumosService:
    """Application service for the consumption/cost report of a version."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.item_repository = OrcamentoItemRepository(session)
        self.custeio_repository = OrcamentoItemCusteioLinhaRepository(session)

    def resumo_da_versao(self, orcamento_versao_id: int) -> ResumoConsumos:
        """Aggregate the consumption/cost summary of one budget version."""
        itens = self.item_repository.list_items_by_versao(orcamento_versao_id)
        item_qt = {item.id: (item.quantidade or _UM) for item in itens}
        ajuste_total = sum(
            ((item.ajuste_eur or _ZERO) * (item.quantidade or _UM) for item in itens),
            _ZERO,
        )

        linhas_consumo = [
            self._linha_consumo(linha, item_qt.get(linha.orcamento_item_id, _UM))
            for linha in self.custeio_repository.list_by_orcamento_versao(
                orcamento_versao_id
            )
            if linha.ativo
        ]

        margens = self.item_repository.get_margens_versao(orcamento_versao_id)
        if margens is None:
            margens = MargensOrcamento()

        return agregar_consumos(linhas_consumo, margens, ajuste_total)

    @staticmethod
    def _linha_consumo(linha, item_qt: Decimal) -> LinhaConsumo:
        """Project a cost-line read model into a domain LinhaConsumo."""
        return LinhaConsumo(
            tipo_linha=linha.tipo_linha,
            item_qt=item_qt,
            unidade=linha.unidade,
            quantidade=linha.quantidade,
            area_m2=linha.area_m2,
            perimetro_ml=linha.perimetro_ml,
            comp_mp=linha.comp_mp,
            larg_mp=linha.larg_mp,
            esp_mp=linha.esp_mp,
            esp_real=linha.esp_real,
            preco_liquido=linha.preco_liquido,
            desperdicio_percentagem=linha.desperdicio_percentagem,
            ref_le=linha.ref_le,
            descricao_no_orcamento=linha.descricao_no_orcamento,
            familia_materia_prima=linha.familia_materia_prima,
            coresp_orla_0_4=linha.coresp_orla_0_4,
            coresp_orla_1_0=linha.coresp_orla_1_0,
            ml_orla_fina=linha.ml_orla_fina,
            ml_orla_grossa=linha.ml_orla_grossa,
            custo_orla_fina=linha.custo_orla_fina,
            custo_orla_grossa=linha.custo_orla_grossa,
            consumo_ml_total=linha.consumo_ml_total,
            custo_mp=linha.custo_mp,
            custo_orlas=linha.custo_orlas,
            custo_ferragem=linha.custo_ferragem,
            custo_acabamento=linha.custo_acabamento,
            custo_producao=linha.custo_producao,
            custo_corte=linha.custo_corte,
            custo_orlagem=linha.custo_orlagem,
            custo_cnc=linha.custo_cnc,
            custo_montagem_manual=linha.custo_montagem_manual,
            excluir_mp=linha.excluir_mp,
            excluir_orla=linha.excluir_orla,
            excluir_ferragem=linha.excluir_ferragem,
            excluir_producao=linha.excluir_producao,
            excluir_acabamento=linha.excluir_acabamento,
            excluir_mo=linha.excluir_mo,
        )
