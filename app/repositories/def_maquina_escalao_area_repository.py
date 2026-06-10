"""Repository for machine area price tiers (phase 8S.0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefMaquinaEscalaoArea


@dataclass(frozen=True)
class DefMaquinaEscalaoAreaResumo:
    """Read model for a machine area price tier."""

    id: int
    def_maquina_id: int
    nivel: int
    area_max_m2: Decimal | None
    preco_peca_std: Decimal | None
    preco_peca_serie: Decimal | None
    ativo: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefMaquinaEscalaoAreaRepository:
    """Repository for DefMaquinaEscalaoArea operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_maquina(self, def_maquina_id: int) -> list[DefMaquinaEscalaoAreaResumo]:
        """List all area tiers of a machine, ordered by level."""
        statement = (
            select(DefMaquinaEscalaoArea)
            .where(DefMaquinaEscalaoArea.def_maquina_id == def_maquina_id)
            .order_by(DefMaquinaEscalaoArea.nivel.asc(), DefMaquinaEscalaoArea.id.asc())
        )
        escaloes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(escalao) for escalao in escaloes]

    def list_active_by_maquina(
        self, def_maquina_id: int
    ) -> list[DefMaquinaEscalaoAreaResumo]:
        """List active area tiers of a machine, ordered by level."""
        statement = (
            select(DefMaquinaEscalaoArea)
            .where(
                DefMaquinaEscalaoArea.def_maquina_id == def_maquina_id,
                DefMaquinaEscalaoArea.ativo.is_(True),
            )
            .order_by(DefMaquinaEscalaoArea.nivel.asc(), DefMaquinaEscalaoArea.id.asc())
        )
        escaloes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(escalao) for escalao in escaloes]

    def get_by_id(self, id: int) -> DefMaquinaEscalaoAreaResumo | None:
        """Get one area tier by id."""
        escalao = self.session.get(DefMaquinaEscalaoArea, id)
        if escalao is None:
            return None

        return self._to_resumo(escalao)

    def create_escalao(
        self,
        *,
        def_maquina_id: int,
        nivel: int = 1,
        area_max_m2: Decimal | None = None,
        preco_peca_std: Decimal | None = None,
        preco_peca_serie: Decimal | None = None,
        ativo: bool = True,
    ) -> DefMaquinaEscalaoAreaResumo:
        """Create one area tier."""
        escalao = DefMaquinaEscalaoArea(
            def_maquina_id=def_maquina_id,
            nivel=nivel,
            area_max_m2=area_max_m2,
            preco_peca_std=preco_peca_std,
            preco_peca_serie=preco_peca_serie,
            ativo=ativo,
        )
        self.session.add(escalao)
        self.session.flush()

        return self._to_resumo(escalao)

    def update_escalao(
        self,
        *,
        id: int,
        nivel: int = 1,
        area_max_m2: Decimal | None = None,
        preco_peca_std: Decimal | None = None,
        preco_peca_serie: Decimal | None = None,
        ativo: bool = True,
    ) -> DefMaquinaEscalaoAreaResumo:
        """Update one area tier."""
        escalao = self.session.get(DefMaquinaEscalaoArea, id)
        if escalao is None:
            raise ValueError("def_maquina_escalao_area not found")

        escalao.nivel = nivel
        escalao.area_max_m2 = area_max_m2
        escalao.preco_peca_std = preco_peca_std
        escalao.preco_peca_serie = preco_peca_serie
        escalao.ativo = ativo
        self.session.flush()

        return self._to_resumo(escalao)

    def deactivate_escalao(self, id: int) -> bool:
        """Deactivate one area tier."""
        escalao = self.session.get(DefMaquinaEscalaoArea, id)
        if escalao is None:
            return False

        escalao.ativo = False
        self.session.flush()

        return True

    def activate_escalao(self, id: int) -> bool:
        """Reactivate one area tier."""
        escalao = self.session.get(DefMaquinaEscalaoArea, id)
        if escalao is None:
            return False

        escalao.ativo = True
        self.session.flush()

        return True

    def _to_resumo(self, escalao: DefMaquinaEscalaoArea) -> DefMaquinaEscalaoAreaResumo:
        """Convert an ORM area tier to the read model."""
        return DefMaquinaEscalaoAreaResumo(
            id=escalao.id,
            def_maquina_id=escalao.def_maquina_id,
            nivel=escalao.nivel,
            area_max_m2=escalao.area_max_m2,
            preco_peca_std=escalao.preco_peca_std,
            preco_peca_serie=escalao.preco_peca_serie,
            ativo=escalao.ativo,
            created_at=escalao.created_at,
            updated_at=escalao.updated_at,
        )
