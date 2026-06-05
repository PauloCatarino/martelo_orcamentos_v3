"""Service for budget item read workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.orcamento_item_repository import OrcamentoItemRepository, OrcamentoItemResumo


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


class OrcamentoItemService:
    """Application service for OrcamentoItem workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoItemRepository(session)

    def list_items_by_versao(self, orcamento_versao_id: int) -> list[OrcamentoItemResumo]:
        """List items for one budget version."""
        return self.repository.list_items_by_versao(orcamento_versao_id)

    def criar_item_simples(self, data: CriarOrcamentoItemSimplesData) -> OrcamentoItemResumo:
        """Create a simple budget item."""
        item_name = data.item.strip()
        unidade = data.unidade.strip() or "un"

        if not item_name:
            raise ValueError("item is required")

        if data.quantidade <= 0:
            raise ValueError("quantidade must be greater than 0")

        ordem = self.repository.get_next_ordem(data.orcamento_versao_id)
        preco_total = data.quantidade * data.preco_unitario

        result = self.repository.create_item(
            orcamento_versao_id=data.orcamento_versao_id,
            ordem=ordem,
            codigo=data.codigo,
            item=item_name,
            descricao=data.descricao,
            altura=data.altura,
            largura=data.largura,
            profundidade=data.profundidade,
            quantidade=data.quantidade,
            unidade=unidade,
            preco_unitario=data.preco_unitario,
            preco_total=preco_total,
        )
        self.recalcular_total_versao(data.orcamento_versao_id)
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

        if not item_name:
            raise ValueError("item is required")

        if data.quantidade <= 0:
            raise ValueError("quantidade must be greater than 0")

        preco_total = data.quantidade * data.preco_unitario

        result = self.repository.update_item(
            item_id=item_id,
            codigo=data.codigo,
            item=item_name,
            descricao=data.descricao,
            altura=data.altura,
            largura=data.largura,
            profundidade=data.profundidade,
            quantidade=data.quantidade,
            unidade=unidade,
            preco_unitario=data.preco_unitario,
            preco_total=preco_total,
        )
        self.recalcular_total_versao(result.orcamento_versao_id)
        self.session.commit()

        return result

    def remover_item(self, item_id: int) -> bool:
        """Remove one budget item."""
        item = self.repository.get_item_by_id(item_id)
        if item is None:
            return False

        deleted = self.repository.delete_item(item_id)
        if deleted:
            self.recalcular_total_versao(item.orcamento_versao_id)
            self.session.commit()

        return deleted

    def recalcular_total_versao(self, orcamento_versao_id: int) -> Decimal:
        """Recalculate and store the total for a budget version."""
        total = self.repository.sum_preco_total_by_versao(orcamento_versao_id)
        self.repository.update_preco_total_versao(orcamento_versao_id, total)

        return total
