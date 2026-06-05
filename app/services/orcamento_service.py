"""Service for budget read workflows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.orcamento_repository import OrcamentoRepository, OrcamentoResumo


class OrcamentoService:
    """Application service for Orcamento workflows."""

    def __init__(self, session: Session) -> None:
        self.repository = OrcamentoRepository(session)

    def list_orcamentos(self) -> list[OrcamentoResumo]:
        """List available budget versions."""
        return self.repository.list_orcamentos()
