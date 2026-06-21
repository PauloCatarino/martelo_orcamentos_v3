"""Repository for budget item reads."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.precos import MargensOrcamento
from app.models import OrcamentoItem, OrcamentoVersao


@dataclass(frozen=True)
class OrcamentoItemResumo:
    """Read model for listing budget items."""

    id: int
    orcamento_versao_id: int
    ordem: int
    codigo: str | None
    item: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal
    unidade: str | None
    preco_unitario: Decimal | None
    preco_total: Decimal | None
    tipo_item: str = "OUTRO"
    tipo_producao: str | None = None
    ajuste_eur: Decimal = Decimal("0")
    preco_manual: bool = False


class OrcamentoItemRepository:
    """Repository for OrcamentoItem read operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_items_by_versao(self, orcamento_versao_id: int) -> list[OrcamentoItemResumo]:
        """List items for one budget version."""
        statement = (
            select(OrcamentoItem)
            .where(OrcamentoItem.orcamento_versao_id == orcamento_versao_id)
            .order_by(OrcamentoItem.ordem.asc())
        )

        items = self.session.execute(statement).scalars().all()

        return [self._to_resumo(item) for item in items]

    def get_next_ordem(self, orcamento_versao_id: int) -> int:
        """Return the next item order for a budget version."""
        statement = select(OrcamentoItem.ordem).where(
            OrcamentoItem.orcamento_versao_id == orcamento_versao_id
        )
        existing_orders = self.session.execute(statement).scalars().all()

        if not existing_orders:
            return 1

        return max(existing_orders) + 1

    def get_item_by_id(self, item_id: int) -> OrcamentoItemResumo | None:
        """Get one item by id."""
        item = self.session.get(OrcamentoItem, item_id)
        if item is None:
            return None

        return self._to_resumo(item)

    def create_item(
        self,
        *,
        orcamento_versao_id: int,
        ordem: int,
        codigo: str | None,
        tipo_item: str,
        item: str,
        descricao: str | None,
        altura: Decimal | None,
        largura: Decimal | None,
        profundidade: Decimal | None,
        quantidade: Decimal,
        unidade: str,
        preco_unitario: Decimal,
        preco_total: Decimal,
        preco_manual: bool = False,
    ) -> OrcamentoItemResumo:
        """Create one budget item."""
        orcamento_item = OrcamentoItem(
            orcamento_versao_id=orcamento_versao_id,
            ordem=ordem,
            codigo=codigo,
            tipo_item=tipo_item,
            item=item,
            descricao=descricao,
            altura=altura,
            largura=largura,
            profundidade=profundidade,
            quantidade=quantidade,
            unidade=unidade,
            preco_unitario=preco_unitario,
            preco_total=preco_total,
            preco_manual=preco_manual,
        )
        self.session.add(orcamento_item)
        self.session.flush()

        return self._to_resumo(orcamento_item)

    def update_item(
        self,
        *,
        item_id: int,
        codigo: str | None,
        tipo_item: str,
        item: str,
        descricao: str | None,
        altura: Decimal | None,
        largura: Decimal | None,
        profundidade: Decimal | None,
        quantidade: Decimal,
        unidade: str,
        preco_unitario: Decimal,
        preco_total: Decimal,
        preco_manual: bool = False,
    ) -> OrcamentoItemResumo:
        """Update one budget item."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            raise ValueError("item not found")

        orcamento_item.codigo = codigo
        orcamento_item.tipo_item = tipo_item
        orcamento_item.item = item
        orcamento_item.descricao = descricao
        orcamento_item.altura = altura
        orcamento_item.largura = largura
        orcamento_item.profundidade = profundidade
        orcamento_item.quantidade = quantidade
        orcamento_item.unidade = unidade
        orcamento_item.preco_unitario = preco_unitario
        orcamento_item.preco_total = preco_total
        orcamento_item.preco_manual = preco_manual
        self.session.flush()

        return self._to_resumo(orcamento_item)

    def delete_item(self, item_id: int) -> bool:
        """Delete one budget item."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            return False

        self.session.delete(orcamento_item)
        self.session.flush()

        return True

    def update_tipo_producao(self, item_id: int, tipo_producao: str | None) -> bool:
        """Set one item's production-type exception (None = inherit the default)."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            return False

        orcamento_item.tipo_producao = tipo_producao
        self.session.flush()

        return True

    def get_tipo_producao_default(self, orcamento_versao_id: int) -> str | None:
        """Return the version's default production type (or None when not found)."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return None

        return versao.tipo_producao_default

    def update_tipo_producao_default(
        self, orcamento_versao_id: int, tipo_producao: str
    ) -> bool:
        """Set the version's default production type."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False

        versao.tipo_producao_default = tipo_producao
        self.session.flush()

        return True

    def get_margens_versao(self, orcamento_versao_id: int) -> MargensOrcamento | None:
        """Return the version's margins (or None when the version is missing)."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return None

        return MargensOrcamento(
            margem_lucro_pct=versao.margem_lucro_pct,
            margem_mp_pct=versao.margem_mp_pct,
            margem_mao_obra_pct=versao.margem_mao_obra_pct,
            margem_acabamentos_pct=versao.margem_acabamentos_pct,
            custos_administrativos_pct=versao.custos_administrativos_pct,
        )

    def update_margens_versao(
        self, orcamento_versao_id: int, margens: MargensOrcamento
    ) -> bool:
        """Store the version's margins."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False

        versao.margem_lucro_pct = margens.margem_lucro_pct
        versao.margem_mp_pct = margens.margem_mp_pct
        versao.margem_mao_obra_pct = margens.margem_mao_obra_pct
        versao.margem_acabamentos_pct = margens.margem_acabamentos_pct
        versao.custos_administrativos_pct = margens.custos_administrativos_pct
        self.session.flush()

        return True

    def update_ajuste_item(self, item_id: int, ajuste_eur: Decimal) -> bool:
        """Set one item's manual price adjustment (EUR)."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            return False

        orcamento_item.ajuste_eur = ajuste_eur
        self.session.flush()

        return True

    def update_preco_item(
        self, item_id: int, preco_unitario: Decimal, preco_total: Decimal
    ) -> bool:
        """Store one item's computed prices."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            return False

        orcamento_item.preco_unitario = preco_unitario
        orcamento_item.preco_total = preco_total
        self.session.flush()

        return True

    def sum_preco_total_by_versao(self, orcamento_versao_id: int) -> Decimal:
        """Return the sum of item totals for one budget version."""
        statement = select(func.coalesce(func.sum(OrcamentoItem.preco_total), 0)).where(
            OrcamentoItem.orcamento_versao_id == orcamento_versao_id
        )
        value = self.session.execute(statement).scalar_one()

        return Decimal(value)

    def update_preco_total_versao(self, orcamento_versao_id: int, preco_total: Decimal) -> bool:
        """Update a budget version total."""
        versao = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if versao is None:
            return False

        versao.preco_total = preco_total
        self.session.flush()

        return True

    def _to_resumo(self, item: OrcamentoItem) -> OrcamentoItemResumo:
        """Convert an ORM item to the read model."""
        return OrcamentoItemResumo(
            id=item.id,
            orcamento_versao_id=item.orcamento_versao_id,
            ordem=item.ordem,
            codigo=item.codigo,
            item=item.item,
            descricao=item.descricao,
            altura=item.altura,
            largura=item.largura,
            profundidade=item.profundidade,
            quantidade=item.quantidade,
            unidade=item.unidade,
            preco_unitario=item.preco_unitario,
            preco_total=item.preco_total,
            tipo_item=item.tipo_item,
            tipo_producao=item.tipo_producao,
            ajuste_eur=item.ajuste_eur,
            preco_manual=item.preco_manual,
        )
