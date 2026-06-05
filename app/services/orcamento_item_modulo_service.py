"""Service for budget item module workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.orcamento_item_modulo_repository import (
    OrcamentoItemModuloRepository,
    OrcamentoItemModuloResumo,
)


@dataclass(frozen=True)
class CriarOrcamentoItemModuloSimplesData:
    """Input data for creating a simple budget item module."""

    orcamento_item_id: int
    nome: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal


@dataclass(frozen=True)
class EditarOrcamentoItemModuloSimplesData:
    """Input data for editing a simple budget item module."""

    nome: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal


class OrcamentoItemModuloService:
    """Application service for OrcamentoItemModulo workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoItemModuloRepository(session)

    def listar_modulos(self, orcamento_item_id: int) -> list[OrcamentoItemModuloResumo]:
        """List modules for one budget item."""
        return self.repository.list_by_item_id(orcamento_item_id)

    def count_by_item_id(self, orcamento_item_id: int) -> int:
        """Count modules for one budget item."""
        return self.repository.count_by_item_id(orcamento_item_id)

    def get_counts_by_item_ids(self, item_ids: list[int]) -> dict[int, int]:
        """Return module counts keyed by budget item id."""
        return self.repository.get_counts_by_item_ids(item_ids)

    def get_modulo_by_id(self, modulo_id: int) -> OrcamentoItemModuloResumo | None:
        """Get one module by id."""
        return self.repository.get_modulo_by_id(modulo_id)

    def criar_modulo_simples(
        self,
        data: CriarOrcamentoItemModuloSimplesData,
    ) -> OrcamentoItemModuloResumo:
        """Create a simple module."""
        nome = data.nome.strip()
        self._validate(nome=nome, quantidade=data.quantidade)

        ordem = self.repository.get_next_ordem(data.orcamento_item_id)
        result = self.repository.create_modulo(
            orcamento_item_id=data.orcamento_item_id,
            ordem=ordem,
            nome=nome,
            descricao=data.descricao,
            altura=data.altura,
            largura=data.largura,
            profundidade=data.profundidade,
            quantidade=data.quantidade,
        )
        self.session.commit()

        return result

    def editar_modulo_simples(
        self,
        modulo_id: int,
        data: EditarOrcamentoItemModuloSimplesData,
    ) -> OrcamentoItemModuloResumo:
        """Edit a simple module."""
        nome = data.nome.strip()
        self._validate(nome=nome, quantidade=data.quantidade)

        result = self.repository.update_modulo(
            modulo_id=modulo_id,
            nome=nome,
            descricao=data.descricao,
            altura=data.altura,
            largura=data.largura,
            profundidade=data.profundidade,
            quantidade=data.quantidade,
        )
        self.session.commit()

        return result

    def remover_modulo(self, modulo_id: int) -> bool:
        """Remove one module."""
        deleted = self.repository.delete_modulo(modulo_id)
        if deleted:
            self.session.commit()

        return deleted

    def _validate(self, *, nome: str, quantidade: Decimal) -> None:
        if not nome:
            raise ValueError("nome is required")

        if quantidade <= 0:
            raise ValueError("quantidade must be greater than 0")
