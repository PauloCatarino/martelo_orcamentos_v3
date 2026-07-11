"""Service that aggregates the consumption/cost of a budget version (phase 8W.0).

Reads the ACTIVE cost lines of every item of the version, multiplies each line
by its item's quantity, and delegates the aggregation to the pure
``app.domain.consumos``. No UI here (the report page is phase 8W.1).
"""

from __future__ import annotations

from decimal import ROUND_CEILING, Decimal

from sqlalchemy.orm import Session

from app.domain.consumos import (
    LinhaConsumo,
    ResumoConsumos,
    agregar_consumos,
    chave_placa,
)
from app.domain.custos import calcular_custo_mp, fator_desperdicio
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
_CEM = Decimal("100")
_MIL = Decimal("1000")
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
        self._aplicar_placa_inteira(orcamento_versao_id, custeio_service)
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

    def _aplicar_placa_inteira(
        self, orcamento_versao_id: int, custeio_service
    ) -> None:
        """Recalculate the waste % of Não-Stock boards to whole-board figures (V2).

        For each board (grouped by ref_le/descricao/esp) the number of WHOLE
        boards needed is derived from the ORIGINAL (material) waste; a single
        ``desp_global`` then makes the lines' material cost equal the whole-board
        cost, and is propagated to every line of that board across all items. The
        original waste is saved (once) in ``desperdicio_percentagem_original`` so
        it can be restored when the board is unmarked. Boards that are not
        Não-Stock but still carry the saved original are restored.

        Runs after each item's pipeline (so custo_mp was computed with the
        original waste) and before pricing. Boards without pieces (m² = 0) or
        without dimensions are ignored.
        """
        chaves_ativas = self.nao_stock_repository.chaves_ativas(orcamento_versao_id)

        itens = self.item_repository.list_items_by_versao(orcamento_versao_id)
        item_qt = {item.id: (item.quantidade or _UM) for item in itens}

        linhas = [
            linha
            for linha in self.custeio_repository.list_by_orcamento_versao(
                orcamento_versao_id
            )
            if linha.ativo and self._eh_m2(linha.unidade)
        ]

        grupos: dict[tuple, list] = {}
        for linha in linhas:
            chave = chave_placa(
                linha.ref_le, linha.descricao_no_orcamento, linha.esp_mp
            )
            grupos.setdefault(chave, []).append(linha)

        itens_afetados: set[int] = set()
        for chave, linhas_placa in grupos.items():
            if chave in chaves_ativas:
                itens_afetados |= self._ativar_placa_inteira(linhas_placa, item_qt)
            else:
                itens_afetados |= self._repor_desperdicio_original(linhas_placa)

        for item_id in itens_afetados:
            custeio_service.recalcular_custo_total_do_item(item_id)
        if itens_afetados:
            self.session.commit()

    def _ativar_placa_inteira(self, linhas_placa, item_qt) -> set[int]:
        """Raise the waste % of one board's lines to the whole-board global %."""
        area_placa = self._area_placa(linhas_placa)
        if area_placa <= 0:
            return set()  # board without dimensions -> ignore

        m2_pecas = _ZERO
        m2_consumidos_orig = _ZERO
        for linha in linhas_placa:
            base = (
                self._num(linha.area_m2)
                * self._num(linha.quantidade)
                * item_qt.get(linha.orcamento_item_id, _UM)
            )
            m2_pecas += base
            m2_consumidos_orig += base * fator_desperdicio(self._desp_original(linha))
        if m2_pecas <= 0:
            return set()  # no pieces -> ignore

        # The ORIGINAL waste sizes how many whole boards are physically needed.
        qt_placas = int(
            (m2_consumidos_orig / area_placa).to_integral_value(ROUND_CEILING)
        )
        # The global % that makes the line cost equal the whole-board cost, stored
        # as a human percentage (e.g. 199.25) so fator_desperdicio reads it right.
        desp_global = ((Decimal(qt_placas) * area_placa) / m2_pecas - _UM) * _CEM

        afetados: set[int] = set()
        for linha in linhas_placa:
            fields: dict = {"desperdicio_percentagem": desp_global}
            if linha.desperdicio_percentagem_original is None:
                # Save the material waste once, so it can be restored later.
                fields["desperdicio_percentagem_original"] = self._num(
                    linha.desperdicio_percentagem
                )
            custo, _ = calcular_custo_mp(
                linha.area_m2,
                linha.quantidade,
                linha.preco_liquido,
                desp_global,
                linha.unidade,
            )
            fields["custo_mp"] = custo
            self.custeio_repository.update_linha(id=linha.id, **fields)
            afetados.add(linha.orcamento_item_id)
        return afetados

    def _repor_desperdicio_original(self, linhas_placa) -> set[int]:
        """Restore the saved original waste % on a board that is no longer Não-Stock."""
        afetados: set[int] = set()
        for linha in linhas_placa:
            if linha.desperdicio_percentagem_original is None:
                continue  # not under a whole-board adjustment -> leave as-is
            desp = linha.desperdicio_percentagem_original
            custo, _ = calcular_custo_mp(
                linha.area_m2,
                linha.quantidade,
                linha.preco_liquido,
                desp,
                linha.unidade,
            )
            self.custeio_repository.update_linha(
                id=linha.id,
                desperdicio_percentagem=desp,
                desperdicio_percentagem_original=None,
                custo_mp=custo,
            )
            afetados.add(linha.orcamento_item_id)
        return afetados

    def _area_placa(self, linhas_placa) -> Decimal:
        """Board area in m² from the first line that has board dimensions."""
        for linha in linhas_placa:
            comp = self._num(linha.comp_mp)
            larg = self._num(linha.larg_mp)
            if comp > 0 and larg > 0:
                return (comp / _MIL) * (larg / _MIL)
        return _ZERO

    @staticmethod
    def _desp_original(linha) -> Decimal | None:
        """The material waste reference: the saved original when set, else current."""
        if linha.desperdicio_percentagem_original is not None:
            return linha.desperdicio_percentagem_original
        return linha.desperdicio_percentagem

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
            desperdicio_percentagem_original=linha.desperdicio_percentagem_original,
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
            operacoes=linha.operacoes,
            maquina=linha.maquina,
            tempo_corte=linha.tempo_corte,
            tempo_orlagem=linha.tempo_orlagem,
            tempo_cnc=linha.tempo_cnc,
            tempo_montagem=linha.tempo_montagem,
            tempo_manual=linha.tempo_manual,
            tempo_setup=linha.tempo_setup,
            excluir_mp=linha.excluir_mp,
            excluir_orla=linha.excluir_orla,
            excluir_ferragem=linha.excluir_ferragem,
            excluir_producao=linha.excluir_producao,
            excluir_acabamento=linha.excluir_acabamento,
            excluir_mo=linha.excluir_mo,
        )
