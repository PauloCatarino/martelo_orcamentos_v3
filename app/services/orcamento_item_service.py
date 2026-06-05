"""Service for budget item read workflows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.orcamento_item_repository import OrcamentoItemRepository, OrcamentoItemResumo


class OrcamentoItemService:
    """Application service for OrcamentoItem workflows."""

    def __init__(self, session: Session) -> None:
        self.repository = OrcamentoItemRepository(session)

    def list_items_by_versao(self, orcamento_versao_id: int) -> list[OrcamentoItemResumo]:
        """List items for one budget version."""
        return self.repository.list_items_by_versao(orcamento_versao_id)
