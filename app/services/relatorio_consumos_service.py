"""Service that aggregates the consumption/cost of a budget version (phase 8W.0).

Reads the ACTIVE cost lines of every item of the version, multiplies each line
by its item's quantity, and delegates the aggregation to the pure
``app.domain.consumos``. No UI here (the report page is phase 8W.1).
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.consumos import (
    LinhaConsumo,
    ResumoConsumos,
    agregar_consumos,
    agregar_placas,
    chave_placa,
)
from app.domain.medidas import normalizar_numero
from app.domain.precos import MargensOrcamento
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.repositories.orcamento_item_repository import OrcamentoItemRepository
from app.repositories.orcamento_versao_placa_nao_stock_repository import (
    OrcamentoVersaoPlacaNaoStockRepository,
    PlacaNaoStockResumo,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)
from app.services.orcamento_item_service import OrcamentoItemService

_UM = Decimal("1")
_ZERO = Decimal("0")
_UNIDADES_M2 = {"M2", "M²", "M2.", "MTQ", "METRO2", "M^2"}


class RelatorioConsumosService:
    """Application service for the consumption/cost report of a version."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.item_repository = OrcamentoItemRepository(session)
        self.custeio_repository = OrcamentoItemCusteioLinhaRepository(session)
        self.nao_stock_repository = OrcamentoVersaoPlacaNaoStockRepository(session)

    def recalcular_versao(self, orcamento_versao_id: int) -> None:
        """Recompute the FULL costing pipeline of every item, apply the Não-Stock
        boards, then apply prices.

        So the report always reflects the current costing state even if the user
        never clicked "Atualizar" inside each item's costing (phase 8W.1.1).
        Reuses the existing per-item pipeline orchestrator and the version price
        application — no duplicated logic.
        """
        custeio_service = OrcamentoItemCusteioLinhaService(self.session)
        for item in self.item_repository.list_items_by_versao(orcamento_versao_id):
            custeio_service.recalcular_item_completo(item.id)
        self._aplicar_nao_stock(orcamento_versao_id, custeio_service)
        OrcamentoItemService(self.session).aplicar_precos_da_versao(
            orcamento_versao_id
        )

    # ----- Não-Stock (phase 8W.2) -----

    def listar_nao_stock(self, orcamento_versao_id: int) -> list[PlacaNaoStockResumo]:
        """List the stored Não-Stock rows of a version."""
        return self.nao_stock_repository.list_by_versao(orcamento_versao_id)

    def guardar_nao_stock(self, orcamento_versao_id: int, estados) -> None:
        """Persist the Não-Stock state of boards.

        ``estados`` is an iterable of (ref_le, descricao, esp, nao_stock).
        """
        for ref_le, descricao, esp, nao_stock in estados:
            self.nao_stock_repository.set_estado(
                orcamento_versao_id, ref_le, descricao, esp, bool(nao_stock)
            )
        self.session.commit()

    def _aplicar_nao_stock(self, orcamento_versao_id: int, custeio_service) -> None:
        """Replace the %-waste MP cost by the whole-board cost on Não-Stock boards.

        For each board marked Não-Stock, the lines' ``custo_mp`` are scaled so
        their total equals C.Placa Usad (qt_placas × área × pliq); the affected
        items' custo_total is recomputed. The pricing step that follows then uses
        the heavier cost. The %-waste figures shown in the report come from the
        aggregation (m² consumidos × pliq), so they remain the theoretical
        reference — only the budget cost changes.
        """
        chaves = self.nao_stock_repository.chaves_ativas(orcamento_versao_id)
        if not chaves:
            return

        itens = self.item_repository.list_items_by_versao(orcamento_versao_id)
        item_qt = {item.id: (item.quantidade or _UM) for item in itens}
        linhas = [
            linha
            for linha in self.custeio_repository.list_by_orcamento_versao(
                orcamento_versao_id
            )
            if linha.ativo and self._eh_m2(linha.unidade)
        ]

        consumo = [
            self._linha_consumo(linha, item_qt.get(linha.orcamento_item_id, _UM))
            for linha in linhas
        ]
        board_por_chave = {
            chave_placa(p.ref_le, p.descricao_no_orcamento, p.esp_mp): p.custo_placa_inteira
            for p in agregar_placas(consumo)
        }

        grupos: dict[tuple, list] = {}
        for linha in linhas:
            chave = chave_placa(linha.ref_le, linha.descricao_no_orcamento, linha.esp_mp)
            if chave in chaves:
                grupos.setdefault(chave, []).append(linha)

        itens_afetados: set[int] = set()
        for chave, linhas_placa in grupos.items():
            soma_atual = sum(
                (self._num(linha.custo_mp) * item_qt.get(linha.orcamento_item_id, _UM)
                 for linha in linhas_placa),
                _ZERO,
            )
            board = board_por_chave.get(chave, _ZERO)
            if soma_atual <= 0:
                continue
            fator = board / soma_atual
            for linha in linhas_placa:
                self.custeio_repository.update_linha(
                    id=linha.id, custo_mp=self._num(linha.custo_mp) * fator
                )
                itens_afetados.add(linha.orcamento_item_id)

        for item_id in itens_afetados:
            custeio_service.recalcular_custo_total_do_item(item_id)

    @staticmethod
    def _eh_m2(unidade) -> bool:
        return (unidade or "").strip().upper() in _UNIDADES_M2

    @staticmethod
    def _num(valor) -> Decimal:
        numero = normalizar_numero(valor)
        return numero if numero is not None else _ZERO

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

        nao_stock_keys = self.nao_stock_repository.chaves_ativas(orcamento_versao_id)

        return agregar_consumos(
            linhas_consumo, margens, ajuste_total, nao_stock_keys
        )

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
