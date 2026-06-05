"""Repository for composite piece component reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefPecaComponente


@dataclass(frozen=True)
class DefPecaComponenteResumo:
    """Read model for listing composite piece components."""

    id: int
    def_peca_pai_id: int
    tipo_componente: str
    def_peca_componente_id: int | None
    referencia_componente: str | None
    descricao: str | None
    ordem: int
    quantidade: Decimal
    regra_quantidade: str | None
    obrigatorio: bool
    ativo: bool
    observacoes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefPecaComponenteRepository:
    """Repository for DefPecaComponente operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_peca_pai_id(self, def_peca_pai_id: int) -> list[DefPecaComponenteResumo]:
        """List components for one parent piece definition."""
        statement = (
            select(DefPecaComponente)
            .where(DefPecaComponente.def_peca_pai_id == def_peca_pai_id)
            .order_by(DefPecaComponente.ordem.asc(), DefPecaComponente.id.asc())
        )
        componentes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(componente) for componente in componentes]

    def get_by_id(self, id: int) -> DefPecaComponenteResumo | None:
        """Get one component by id."""
        componente = self.session.get(DefPecaComponente, id)
        if componente is None:
            return None

        return self._to_resumo(componente)

    def get_next_ordem(self, def_peca_pai_id: int) -> int:
        """Return the next component order for a parent piece definition."""
        statement = select(DefPecaComponente.ordem).where(
            DefPecaComponente.def_peca_pai_id == def_peca_pai_id
        )
        existing_orders = self.session.execute(statement).scalars().all()

        if not existing_orders:
            return 1

        return max(existing_orders) + 1

    def create_componente(
        self,
        *,
        def_peca_pai_id: int,
        tipo_componente: str,
        def_peca_componente_id: int | None,
        referencia_componente: str | None,
        descricao: str | None,
        ordem: int,
        quantidade: Decimal,
        regra_quantidade: str,
        obrigatorio: bool,
        ativo: bool,
        observacoes: str | None,
    ) -> DefPecaComponenteResumo:
        """Create one composite piece component."""
        componente = DefPecaComponente(
            def_peca_pai_id=def_peca_pai_id,
            tipo_componente=tipo_componente,
            def_peca_componente_id=def_peca_componente_id,
            referencia_componente=referencia_componente,
            descricao=descricao,
            ordem=ordem,
            quantidade=quantidade,
            regra_quantidade=regra_quantidade,
            obrigatorio=obrigatorio,
            ativo=ativo,
            observacoes=observacoes,
        )
        self.session.add(componente)
        self.session.flush()

        return self._to_resumo(componente)

    def update_componente(
        self,
        *,
        id: int,
        def_peca_pai_id: int,
        tipo_componente: str,
        def_peca_componente_id: int | None,
        referencia_componente: str | None,
        descricao: str | None,
        ordem: int,
        quantidade: Decimal,
        regra_quantidade: str,
        obrigatorio: bool,
        ativo: bool,
        observacoes: str | None,
    ) -> DefPecaComponenteResumo:
        """Update one composite piece component."""
        componente = self.session.get(DefPecaComponente, id)
        if componente is None:
            raise ValueError("def_peca_componente not found")

        componente.def_peca_pai_id = def_peca_pai_id
        componente.tipo_componente = tipo_componente
        componente.def_peca_componente_id = def_peca_componente_id
        componente.referencia_componente = referencia_componente
        componente.descricao = descricao
        componente.ordem = ordem
        componente.quantidade = quantidade
        componente.regra_quantidade = regra_quantidade
        componente.obrigatorio = obrigatorio
        componente.ativo = ativo
        componente.observacoes = observacoes
        self.session.flush()

        return self._to_resumo(componente)

    def deactivate_componente(self, id: int) -> bool:
        """Deactivate one composite piece component."""
        componente = self.session.get(DefPecaComponente, id)
        if componente is None:
            return False

        componente.ativo = False
        self.session.flush()

        return True

    def _to_resumo(self, componente: DefPecaComponente) -> DefPecaComponenteResumo:
        """Convert an ORM component to the read model."""
        return DefPecaComponenteResumo(
            id=componente.id,
            def_peca_pai_id=componente.def_peca_pai_id,
            tipo_componente=componente.tipo_componente,
            def_peca_componente_id=componente.def_peca_componente_id,
            referencia_componente=componente.referencia_componente,
            descricao=componente.descricao,
            ordem=componente.ordem,
            quantidade=componente.quantidade,
            regra_quantidade=componente.regra_quantidade,
            obrigatorio=componente.obrigatorio,
            ativo=componente.ativo,
            observacoes=componente.observacoes,
            created_at=componente.created_at,
            updated_at=componente.updated_at,
        )
