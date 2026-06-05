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

        return OrcamentoItemResumo(
            id=orcamento_item.id,
            ordem=orcamento_item.ordem,
            codigo=orcamento_item.codigo,
            item=orcamento_item.item,
            descricao=orcamento_item.descricao,
            altura=orcamento_item.altura,
            largura=orcamento_item.largura,
            profundidade=orcamento_item.profundidade,
            quantidade=orcamento_item.quantidade,
            unidade=orcamento_item.unidade,
            preco_unitario=orcamento_item.preco_unitario,
            preco_total=orcamento_item.preco_total,
        )
