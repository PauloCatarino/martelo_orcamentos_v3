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
