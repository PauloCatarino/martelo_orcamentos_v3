"""Repository for budget item reads."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrcamentoItem


@dataclass(frozen=True)
class OrcamentoItemResumo:
    """Read model for listing budget items."""

    id: int
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

        return [
            OrcamentoItemResumo(
                id=item.id,
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
            )
            for item in items
        ]

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
        item: str,
        descricao: str | None,
        altura: Decimal | None,
        largura: Decimal | None,
        profundidade: Decimal | None,
        quantidade: Decimal,
        unidade: str,
        preco_unitario: Decimal,
        preco_total: Decimal,
    ) -> OrcamentoItemResumo:
        """Create one budget item."""
        orcamento_item = OrcamentoItem(
            orcamento_versao_id=orcamento_versao_id,
            ordem=ordem,
            codigo=codigo,
            item=item,
            descricao=descricao,
            altura=altura,
            largura=largura,
            profundidade=profundidade,
            quantidade=quantidade,
            unidade=unidade,
            preco_unitario=preco_unitario,
            preco_total=preco_total,
        )
        self.session.add(orcamento_item)
        self.session.flush()

        return self._to_resumo(orcamento_item)

    def update_item(
        self,
        *,
        item_id: int,
        codigo: str | None,
        item: str,
        descricao: str | None,
        altura: Decimal | None,
        largura: Decimal | None,
        profundidade: Decimal | None,
        quantidade: Decimal,
        unidade: str,
        preco_unitario: Decimal,
        preco_total: Decimal,
    ) -> OrcamentoItemResumo:
        """Update one budget item."""
        orcamento_item = self.session.get(OrcamentoItem, item_id)
        if orcamento_item is None:
            raise ValueError("item not found")

        orcamento_item.codigo = codigo
        orcamento_item.item = item
        orcamento_item.descricao = descricao
        orcamento_item.altura = altura
        orcamento_item.largura = largura
        orcamento_item.profundidade = profundidade
        orcamento_item.quantidade = quantidade
        orcamento_item.unidade = unidade
        orcamento_item.preco_unitario = preco_unitario
        orcamento_item.preco_total = preco_total
        self.session.flush()

        return self._to_resumo(orcamento_item)

    def _to_resumo(self, item: OrcamentoItem) -> OrcamentoItemResumo:
        """Convert an ORM item to the read model."""
        return OrcamentoItemResumo(
            id=item.id,
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
        )
