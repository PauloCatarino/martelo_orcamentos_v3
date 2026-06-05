"""Repository for budget item module reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import OrcamentoItemModulo


@dataclass(frozen=True)
class OrcamentoItemModuloResumo:
    """Read model for listing budget item modules."""

    id: int
    orcamento_item_id: int
    ordem: int
    nome: str
    descricao: str | None
    altura: Decimal | None
    largura: Decimal | None
    profundidade: Decimal | None
    quantidade: Decimal


class OrcamentoItemModuloRepository:
    """Repository for OrcamentoItemModulo operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_item_id(self, orcamento_item_id: int) -> list[OrcamentoItemModuloResumo]:
        """List modules for one budget item."""
        statement = (
            select(OrcamentoItemModulo)
            .where(OrcamentoItemModulo.orcamento_item_id == orcamento_item_id)
            .order_by(OrcamentoItemModulo.ordem.asc())
        )
        modulos = self.session.execute(statement).scalars().all()

        return [self._to_resumo(modulo) for modulo in modulos]

    def count_by_item_id(self, orcamento_item_id: int) -> int:
        """Count modules for one budget item."""
        statement = select(func.count(OrcamentoItemModulo.id)).where(
            OrcamentoItemModulo.orcamento_item_id == orcamento_item_id
        )

        return int(self.session.execute(statement).scalar_one())

    def get_counts_by_item_ids(self, item_ids: list[int]) -> dict[int, int]:
        """Return module counts keyed by budget item id."""
        if not item_ids:
            return {}

        statement = (
            select(
                OrcamentoItemModulo.orcamento_item_id,
                func.count(OrcamentoItemModulo.id),
            )
            .where(OrcamentoItemModulo.orcamento_item_id.in_(item_ids))
            .group_by(OrcamentoItemModulo.orcamento_item_id)
        )
        rows = self.session.execute(statement).all()
        counts = {int(item_id): int(count) for item_id, count in rows}

        return {item_id: counts.get(item_id, 0) for item_id in item_ids}

    def get_next_ordem(self, orcamento_item_id: int) -> int:
        """Return the next module order for an item."""
        statement = select(OrcamentoItemModulo.ordem).where(
            OrcamentoItemModulo.orcamento_item_id == orcamento_item_id
        )
        existing_orders = self.session.execute(statement).scalars().all()

        if not existing_orders:
            return 1

        return max(existing_orders) + 1

    def create_modulo(
        self,
        *,
        orcamento_item_id: int,
        ordem: int,
        nome: str,
        descricao: str | None,
        altura: Decimal | None,
        largura: Decimal | None,
        profundidade: Decimal | None,
        quantidade: Decimal,
    ) -> OrcamentoItemModuloResumo:
        """Create one module."""
        modulo = OrcamentoItemModulo(
            orcamento_item_id=orcamento_item_id,
            ordem=ordem,
            nome=nome,
            descricao=descricao,
            altura=altura,
            largura=largura,
            profundidade=profundidade,
            quantidade=quantidade,
        )
        self.session.add(modulo)
        self.session.flush()

        return self._to_resumo(modulo)

    def get_modulo_by_id(self, modulo_id: int) -> OrcamentoItemModuloResumo | None:
        """Get one module by id."""
        modulo = self.session.get(OrcamentoItemModulo, modulo_id)
        if modulo is None:
            return None

        return self._to_resumo(modulo)

    def update_modulo(
        self,
        *,
        modulo_id: int,
        nome: str,
        descricao: str | None,
        altura: Decimal | None,
        largura: Decimal | None,
        profundidade: Decimal | None,
        quantidade: Decimal,
    ) -> OrcamentoItemModuloResumo:
        """Update one module."""
        modulo = self.session.get(OrcamentoItemModulo, modulo_id)
        if modulo is None:
            raise ValueError("modulo not found")

        modulo.nome = nome
        modulo.descricao = descricao
        modulo.altura = altura
        modulo.largura = largura
        modulo.profundidade = profundidade
        modulo.quantidade = quantidade
        self.session.flush()

        return self._to_resumo(modulo)

    def delete_modulo(self, modulo_id: int) -> bool:
        """Delete one module."""
        modulo = self.session.get(OrcamentoItemModulo, modulo_id)
        if modulo is None:
            return False

        self.session.delete(modulo)
        self.session.flush()

        return True

    def _to_resumo(self, modulo: OrcamentoItemModulo) -> OrcamentoItemModuloResumo:
        """Convert an ORM module to the read model."""
        return OrcamentoItemModuloResumo(
            id=modulo.id,
            orcamento_item_id=modulo.orcamento_item_id,
            ordem=modulo.ordem,
            nome=modulo.nome,
            descricao=modulo.descricao,
            altura=modulo.altura,
            largura=modulo.largura,
            profundidade=modulo.profundidade,
            quantidade=modulo.quantidade,
        )
