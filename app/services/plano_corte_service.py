"""Serviço (fino) dos dados do plano de corte (C3.2).

Liga o domínio puro (:mod:`app.domain.plano_corte_dados`) à versão do orçamento,
seguindo o mesmo padrão do ``OrcamentoExportService.exportar_resumo_custos``.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.plano_corte_dados import GrupoCorte, construir_grupos_corte
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.repositories.orcamento_item_repository import OrcamentoItemRepository
from app.services.relatorio_consumos_service import RelatorioConsumosService
from app.services.resumo_custos_excel_export import construir_linhas_geral


class PlanoCorteService:
    """Application service para os dados do plano de corte de uma versão."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def dados_plano_corte(self, orcamento_versao_id: int) -> list[GrupoCorte]:
        """Recalcula a versão e devolve os grupos de peças de placa."""
        relatorio = RelatorioConsumosService(self.session)
        relatorio.recalcular_versao(orcamento_versao_id)
        resumo = relatorio.resumo_da_versao(orcamento_versao_id)

        itens = OrcamentoItemRepository(self.session).list_items_by_versao(
            orcamento_versao_id
        )
        item_qt = {item.id: (item.quantidade or Decimal("1")) for item in itens}
        linhas = OrcamentoItemCusteioLinhaRepository(
            self.session
        ).list_by_orcamento_versao(orcamento_versao_id)
        linhas_geral = construir_linhas_geral(
            [linha for linha in linhas if linha.ativo], item_qt
        )

        return construir_grupos_corte(
            linhas_geral, getattr(resumo, "placas", None) or []
        )
