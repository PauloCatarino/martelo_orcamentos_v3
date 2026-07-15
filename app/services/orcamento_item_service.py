"""Service for budget item read workflows."""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy.orm import Session

from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    PECA_COMPOSTA,
    SEPARADOR,
)
from app.domain.item_types import normalize_item_type
from app.domain.numeros import validar_decimal
from app.domain.precos import (
    BlocosCusto,
    ItemObjetivo,
    MargensOrcamento,
    ResultadoObjetivo,
    atingir_objetivo,
    blocos_custo_da_linha,
    calcular_preco_total,
    calcular_preco_unitario,
    somar_blocos_custo,
)
from app.domain.producao_types import (
    TIPO_PRODUCAO_STD,
    normalize_tipo_producao,
    tipo_producao_efetivo,
)
from app.domain.custeio_simplificado import (
    MODALIDADE_CUSTEIO_SIMPLIFICADO,
    normalizar_modalidade_custeio,
)
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.repositories.orcamento_item_repository import OrcamentoItemRepository, OrcamentoItemResumo
from app.services.orcamento_historico_service import OrcamentoHistoricoService

_CENTIMOS = Decimal("0.01")


@dataclass(frozen=True)
class CriarOrcamentoItemSimplesData:
    """Input data for creating a simple budget item."""

    orcamento_versao_id: int
    codigo: str | None
    item: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal
    unidade: str
    preco_unitario: Decimal
    tipo_item: str | None = None
    preco_manual: bool = False


@dataclass(frozen=True)
class EditarOrcamentoItemSimplesData:
    """Input data for editing a simple budget item."""

    codigo: str | None
    item: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal
    unidade: str
    preco_unitario: Decimal
    tipo_item: str | None = None
    preco_manual: bool = False


@dataclass(frozen=True)
class AplicarPrecosResult:
    """Outcome of applying the version margins to its items."""

    itens_atualizados: int
    itens_sem_custeio: int
    soma_preco_total: Decimal


@dataclass(frozen=True)
class PrecoItemResult:
    """Produced cost and stored prices of one item after re-pricing.

    ``custo_produzido`` is 0 for items without costable lines (their manual
    price is kept; ``preco_unitario``/``preco_total`` then echo that price).
    """

    custo_produzido: Decimal
    preco_unitario: Decimal | None
    preco_total: Decimal | None


class OrcamentoItemService:
    """Application service for OrcamentoItem workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoItemRepository(session)
        self.custeio_repository = OrcamentoItemCusteioLinhaRepository(session)

    def list_items_by_versao(self, orcamento_versao_id: int) -> list[OrcamentoItemResumo]:
        """List items for one budget version."""
        return self.repository.list_items_by_versao(orcamento_versao_id)

    def criar_item_simples(self, data: CriarOrcamentoItemSimplesData) -> OrcamentoItemResumo:
        """Create a simple budget item."""
        item_name = data.item.strip()
        unidade = data.unidade.strip() or "un"
        tipo_item = normalize_item_type(data.tipo_item)

        if not item_name:
            raise ValueError("item is required")

        valores = self._validar_valores_item(data)

        ordem = self.repository.get_next_ordem(data.orcamento_versao_id)
        preco_total = valores["quantidade"] * valores["preco_unitario"]

        result = self.repository.create_item(
            orcamento_versao_id=data.orcamento_versao_id,
            ordem=ordem,
            codigo=data.codigo,
            tipo_item=tipo_item,
            item=item_name,
            descricao=data.descricao,
            altura=valores["altura"],
            largura=valores["largura"],
            profundidade=valores["profundidade"],
            quantidade=valores["quantidade"],
            unidade=unidade,
            preco_unitario=valores["preco_unitario"],
            preco_total=preco_total,
            preco_manual=data.preco_manual,
        )
        self.recalcular_total_versao(data.orcamento_versao_id)
        label = f"{result.codigo} - {result.item}" if result.codigo else result.item
        OrcamentoHistoricoService(self.session).registar(
            data.orcamento_versao_id, "item", f"Item adicionado: {label}"
        )
        self.session.commit()

        return result

    def get_item_by_id(self, item_id: int) -> OrcamentoItemResumo | None:
        """Get one item by id."""
        return self.repository.get_item_by_id(item_id)

    def editar_item_simples(
        self,
        item_id: int,
        data: EditarOrcamentoItemSimplesData,
    ) -> OrcamentoItemResumo:
        """Edit a simple budget item."""
        item_name = data.item.strip()
        unidade = data.unidade.strip() or "un"
        tipo_item = normalize_item_type(data.tipo_item)

        if not item_name:
            raise ValueError("item is required")

        valores = self._validar_valores_item(data)

        preco_total = valores["quantidade"] * valores["preco_unitario"]
        item_anterior = self.repository.get_item_by_id(item_id)

        result = self.repository.update_item(
            item_id=item_id,
            codigo=data.codigo,
            tipo_item=tipo_item,
            item=item_name,
            descricao=data.descricao,
            altura=valores["altura"],
            largura=valores["largura"],
            profundidade=valores["profundidade"],
            quantidade=valores["quantidade"],
            unidade=unidade,
            preco_unitario=valores["preco_unitario"],
            preco_total=preco_total,
            preco_manual=data.preco_manual,
        )
        self.recalcular_total_versao(result.orcamento_versao_id)
        label = f"{result.codigo} - {result.item}" if result.codigo else result.item
        manual_antes = bool(item_anterior and item_anterior.preco_manual)
        if data.preco_manual and not manual_antes:
            descricao_evento = f"Pre\u00e7o manual aplicado ao item {label}"
        elif manual_antes and not data.preco_manual:
            descricao_evento = f"Pre\u00e7o manual removido do item {label}"
        else:
            descricao_evento = f"Item editado: {label}"
        OrcamentoHistoricoService(self.session).registar(
            result.orcamento_versao_id, "item", descricao_evento
        )
        self.session.commit()

        return result

    @staticmethod
    def _validar_valores_item(data) -> dict[str, Decimal | None]:
        """Validate values that can directly affect item quantities and prices."""
        valores: dict[str, Decimal | None] = {}
        for campo, rotulo in (
            ("altura", "Altura"),
            ("largura", "Largura"),
            ("profundidade", "Profundidade"),
        ):
            valores[campo] = validar_decimal(
                getattr(data, campo),
                rotulo,
                minimo=Decimal("0"),
                minimo_exclusivo=True,
            )
        valores["quantidade"] = validar_decimal(
            data.quantidade,
            "quantidade",
            permitir_vazio=False,
            minimo=Decimal("0"),
            minimo_exclusivo=True,
        )
        valores["preco_unitario"] = validar_decimal(
            data.preco_unitario,
            "Preço unitário",
            permitir_vazio=False,
            minimo=Decimal("0"),
        )
        return valores

    def remover_item(self, item_id: int) -> bool:
        """Remove one budget item."""
        item = self.repository.get_item_by_id(item_id)
        if item is None:
            return False

        deleted = self.repository.delete_item(item_id)
        if deleted:
            self.recalcular_total_versao(item.orcamento_versao_id)
            label = f"{item.codigo} - {item.item}" if item.codigo else item.item
            OrcamentoHistoricoService(self.session).registar(
                item.orcamento_versao_id, "item", f"Item removido: {label}"
            )
            self.session.commit()

        return deleted

    def recalcular_total_versao(self, orcamento_versao_id: int) -> Decimal:
        """Recalculate and store the total for a budget version."""
        total = self.repository.sum_preco_total_by_versao(orcamento_versao_id)
        self.repository.update_preco_total_versao(orcamento_versao_id, total)

        return total

    def get_margens_versao(self, orcamento_versao_id: int) -> MargensOrcamento:
        """Return the version's margins (zeros when the version is missing)."""
        margens = self.repository.get_margens_versao(orcamento_versao_id)
        return margens if margens is not None else MargensOrcamento()

    def definir_margens_versao(
        self, orcamento_versao_id: int, margens: MargensOrcamento
    ) -> AplicarPrecosResult:
        """Store the version's margins and re-apply the price formula."""
        anteriores = self.get_margens_versao(orcamento_versao_id)
        if not self.repository.update_margens_versao(orcamento_versao_id, margens):
            raise ValueError("orcamento_versao not found")
        self._registar_margens_alteradas(orcamento_versao_id, anteriores, margens)
        return self.aplicar_precos_da_versao(orcamento_versao_id)

    def _registar_margens_alteradas(
        self,
        orcamento_versao_id: int,
        anteriores: MargensOrcamento,
        novas: MargensOrcamento,
    ) -> None:
        campos = [
            ("margem_lucro_pct", "Lucro"),
            ("margem_mp_pct", "MP"),
            ("margem_mao_obra_pct", "M\u00e3o de obra"),
            ("margem_acabamentos_pct", "Acabamentos"),
            ("custos_administrativos_pct", "Custos admin"),
        ]

        def fmt(valor) -> str:
            texto = f"{valor:f}"
            if "." in texto:
                texto = texto.rstrip("0").rstrip(".")
            return f"{texto}%"

        mudancas = [
            f"{rotulo} {fmt(getattr(anteriores, attr))} \u2192 {fmt(getattr(novas, attr))}"
            for attr, rotulo in campos
            if getattr(anteriores, attr) != getattr(novas, attr)
        ]
        if mudancas:
            OrcamentoHistoricoService(self.session).registar(
                orcamento_versao_id, "margens", "Margens: " + "; ".join(mudancas)
            )

    def get_blocos_custo_por_item(
        self, orcamento_versao_id: int
    ) -> dict[int, BlocosCusto]:
        """Map item id -> cost blocks, for the items WITH active cost lines.

        Items without costable lines are absent from the map (they keep their
        manual price). Division and composite-parent lines are skipped and the
        per-line exclusion flags are honoured — the same rules used by the
        lines' custo_total.
        """
        blocos_por_item: dict[int, list[BlocosCusto]] = {}
        for linha in self.custeio_repository.list_by_orcamento_versao(
            orcamento_versao_id
        ):
            if not linha.ativo:
                continue
            if linha.tipo_linha in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR):
                continue

            blocos_por_item.setdefault(linha.orcamento_item_id, []).append(
                self._blocos_da_linha(linha)
            )

        return {
            item_id: self._adicionar_opcoes_simplificado(
                self.repository.get_item_by_id(item_id), somar_blocos_custo(blocos)
            )
            for item_id, blocos in blocos_por_item.items()
        }

    def aplicar_precos_da_versao(self, orcamento_versao_id: int) -> AplicarPrecosResult:
        """Apply the version margins to every item with cost lines.

        The computed price REPLACES the item's price; items without cost lines
        keep their manual price. Updates the version total and commits.
        """
        margens = self.get_margens_versao(orcamento_versao_id)
        blocos_por_item = self.get_blocos_custo_por_item(orcamento_versao_id)

        atualizados = 0
        sem_custeio = 0
        for item in self.repository.list_items_by_versao(orcamento_versao_id):
            if item.preco_manual:
                # Manual price: the costing must not touch it.
                continue
            blocos = blocos_por_item.get(item.id)
            if blocos is None:
                sem_custeio += 1
                continue

            self._gravar_preco_item(item, blocos, margens)
            atualizados += 1

        total = self.recalcular_total_versao(orcamento_versao_id)
        self.session.commit()

        return AplicarPrecosResult(
            itens_atualizados=atualizados,
            itens_sem_custeio=sem_custeio,
            soma_preco_total=total,
        )

    def resolver_objetivo_preco(
        self, orcamento_versao_id: int, objetivo: Decimal
    ) -> ResultadoObjetivo:
        """Resolve the margins needed for a desired final total (no write).

        Pure preview: reads the version margins, the per-item cost blocks and
        the items, then runs the analytic resolution. Items without costing
        contribute their stored preco_total as a constant (like the EUR
        adjustment). The caller applies the result via definir_margens_versao.
        """
        margens = self.get_margens_versao(orcamento_versao_id)
        blocos_por_item = self.get_blocos_custo_por_item(orcamento_versao_id)

        itens: list[ItemObjetivo] = []
        constante_manual = Decimal("0")
        for item in self.repository.list_items_by_versao(orcamento_versao_id):
            blocos = blocos_por_item.get(item.id)
            # Itens com preco MANUAL nao escalam com as margens
            # (aplicar_precos_da_versao salta-os): entram como CONSTANTE,
            # tal como os itens sem custeio.
            if blocos is None or item.preco_manual:
                if item.preco_total is not None:
                    constante_manual += item.preco_total
                continue

            ajuste = item.ajuste_eur if item.ajuste_eur is not None else Decimal("0")
            quantidade = (
                item.quantidade if item.quantidade is not None else Decimal("1")
            )
            itens.append(
                ItemObjetivo(
                    bloco_mp=blocos.bloco_mp,
                    bloco_producao=blocos.bloco_producao,
                    bloco_acabamento=blocos.bloco_acabamento,
                    ajuste_eur=ajuste,
                    quantidade=quantidade,
                )
            )

        return atingir_objetivo(itens, constante_manual, margens, objetivo)

    def definir_ajuste_item(self, item_id: int, ajuste_eur: Decimal) -> Decimal:
        """Set one item's manual adjustment and re-apply its price formula.

        Items without cost lines keep their manual price (the adjustment is
        stored for when costing exists).
        """
        item = self.repository.get_item_by_id(item_id)
        if item is None:
            raise ValueError("item not found")

        ajuste = ajuste_eur if ajuste_eur is not None else Decimal("0")
        self.repository.update_ajuste_item(item_id, ajuste)

        blocos = self._blocos_do_item(item_id)
        if blocos is not None and not item.preco_manual:
            margens = self.get_margens_versao(item.orcamento_versao_id)
            item_atual = self.repository.get_item_by_id(item_id)
            self._gravar_preco_item(item_atual, blocos, margens)
            self.recalcular_total_versao(item.orcamento_versao_id)

        self.session.commit()

        return ajuste

    def recalcular_preco_item(self, orcamento_item_id: int) -> PrecoItemResult:
        """Recompute and store one item's price from its current cost lines.

        Reuses the version margins and the item's cost blocks (from the costs
        already stored on the lines — no costing pipeline recompute). The
        computed price replaces the item's price; items without costable lines
        keep their manual price and report a produced cost of 0. Returns the
        produced cost and the stored unit/total prices; updates the version
        total and commits. This is the reference value the item takes to the
        items list.
        """
        item = self.repository.get_item_by_id(orcamento_item_id)
        if item is None:
            raise ValueError("item not found")

        if item.preco_manual:
            # Manual price: show the produced cost for comparison, but never
            # overwrite the user's price.
            blocos = self._blocos_do_item(orcamento_item_id)
            custo = blocos.custo_produzido if blocos is not None else Decimal("0")
            return PrecoItemResult(
                custo_produzido=custo,
                preco_unitario=item.preco_unitario,
                preco_total=item.preco_total,
            )

        blocos = self._blocos_do_item(orcamento_item_id)
        if blocos is None:
            # No costing lines: keep the manual price; produced cost is 0.
            return PrecoItemResult(
                custo_produzido=Decimal("0"),
                preco_unitario=item.preco_unitario,
                preco_total=item.preco_total,
            )

        margens = self.get_margens_versao(item.orcamento_versao_id)
        preco_unitario, preco_total = self._gravar_preco_item(item, blocos, margens)
        self.recalcular_total_versao(item.orcamento_versao_id)
        self.session.commit()

        return PrecoItemResult(
            custo_produzido=blocos.custo_produzido,
            preco_unitario=preco_unitario,
            preco_total=preco_total,
        )

    def _blocos_do_item(self, orcamento_item_id: int) -> BlocosCusto | None:
        """Cost blocks of one item, or None when it has no costable lines."""
        blocos = [
            self._blocos_da_linha(linha)
            for linha in self.custeio_repository.list_active_by_orcamento_item(
                orcamento_item_id
            )
            if linha.tipo_linha not in (DIVISAO_INDEPENDENTE, PECA_COMPOSTA, SEPARADOR)
        ]
        if not blocos:
            return None

        return self._adicionar_opcoes_simplificado(
            self.repository.get_item_by_id(orcamento_item_id), somar_blocos_custo(blocos)
        )

    @staticmethod
    def _adicionar_opcoes_simplificado(item, blocos: BlocosCusto) -> BlocosCusto:
        """Append the two item-level simplified charges to the labour block."""
        if item is None or normalizar_modalidade_custeio(item.modalidade_custeio) != MODALIDADE_CUSTEIO_SIMPLIFICADO:
            return blocos
        adicional = (item.custo_simplificado_urgencia or Decimal("0")) + (
            item.custo_simplificado_sem_excel or Decimal("0")
        )
        return replace(
            blocos,
            bloco_producao=blocos.bloco_producao + adicional,
            parcela_montagem_manual=blocos.parcela_montagem_manual + adicional,
        )

    @staticmethod
    def _blocos_da_linha(linha) -> BlocosCusto:
        """Split one cost line into price blocks, honouring its exclusions."""
        return blocos_custo_da_linha(
            custo_mp=linha.custo_mp,
            custo_orlas=linha.custo_orlas,
            custo_ferragem=linha.custo_ferragem,
            custo_acabamento=linha.custo_acabamento,
            custo_producao=linha.custo_producao,
            custo_corte=linha.custo_corte,
            custo_orlagem=linha.custo_orlagem,
            custo_cnc=linha.custo_cnc,
            custo_montagem_manual=linha.custo_montagem_manual,
            fator_serie=linha.fator_serie,
            excluir_mp=linha.excluir_mp,
            excluir_orla=linha.excluir_orla,
            excluir_ferragem=linha.excluir_ferragem,
            excluir_acabamento=linha.excluir_acabamento,
            excluir_producao=linha.excluir_producao,
        )

    def _gravar_preco_item(
        self,
        item: OrcamentoItemResumo,
        blocos: BlocosCusto,
        margens: MargensOrcamento,
    ) -> tuple[Decimal, Decimal]:
        """Compute and store one item's prices from its blocks and the margins.

        preco_total is computed from the full-precision unit price (and only
        then rounded), so it matches the formula rather than the rounded
        preco_unitario. Returns the stored (preco_unitario, preco_total) (2 dp).
        """
        preco_unitario = calcular_preco_unitario(blocos, margens, item.ajuste_eur)
        preco_total = calcular_preco_total(preco_unitario, item.quantidade)
        preco_unitario_q = preco_unitario.quantize(_CENTIMOS, rounding=ROUND_HALF_UP)
        preco_total_q = preco_total.quantize(_CENTIMOS, rounding=ROUND_HALF_UP)
        self.repository.update_preco_item(item.id, preco_unitario_q, preco_total_q)

        return preco_unitario_q, preco_total_q

    def get_tipo_producao_default(self, orcamento_versao_id: int) -> str:
        """Return the version's default production type (STD when unset)."""
        valor = self.repository.get_tipo_producao_default(orcamento_versao_id)
        return normalize_tipo_producao(valor) or TIPO_PRODUCAO_STD

    def definir_tipo_producao_default(
        self, orcamento_versao_id: int, tipo_producao: str
    ) -> str:
        """Set the version's default production type ('STD'/'SERIE')."""
        tipo = normalize_tipo_producao(tipo_producao)
        if tipo is None:
            raise ValueError("tipo_producao invalido")

        if not self.repository.update_tipo_producao_default(orcamento_versao_id, tipo):
            raise ValueError("orcamento_versao not found")
        self.session.commit()

        return tipo

    def definir_tipo_producao_item(
        self, item_id: int, tipo_producao: str | None
    ) -> str | None:
        """Set one item's production-type exception (None = inherit the default)."""
        tipo = normalize_tipo_producao(tipo_producao)
        if tipo_producao is not None and tipo is None:
            raise ValueError("tipo_producao invalido")

        if not self.repository.update_tipo_producao(item_id, tipo):
            raise ValueError("item not found")
        self.session.commit()

        return tipo

    def definir_modalidade_custeio_item(self, item_id: int, modalidade: str) -> str:
        modo = normalizar_modalidade_custeio(modalidade)
        if not self.repository.update_modalidade_custeio(item_id, modo):
            raise ValueError("item not found")
        self.session.commit()
        return modo

    def definir_opcoes_simplificado_item(
        self, item_id: int, *, urgente: bool, sem_excel: bool
    ) -> None:
        if not self.repository.update_modalidade_custeio(
            item_id, MODALIDADE_CUSTEIO_SIMPLIFICADO,
            urgente=urgente, sem_excel=sem_excel,
        ):
            raise ValueError("item not found")
        self.session.commit()

    def get_tipo_producao_efetivo(self, item: OrcamentoItemResumo) -> str:
        """Resolve the effective production type of an item (exception or default)."""
        return tipo_producao_efetivo(
            item.tipo_producao,
            self.repository.get_tipo_producao_default(item.orcamento_versao_id),
        )
