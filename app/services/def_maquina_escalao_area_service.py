"""Service for machine area price tiers (phase 8S.0)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.def_maquina_escalao_area_repository import (
    DefMaquinaEscalaoAreaRepository,
    DefMaquinaEscalaoAreaResumo,
)


@dataclass(frozen=True)
class CriarEscalaoAreaData:
    """Input data for creating a machine area tier."""

    def_maquina_id: int | None
    nivel: int = 1
    area_max_m2: Decimal | None = None
    preco_peca_std: Decimal | None = None
    preco_peca_serie: Decimal | None = None
    ativo: bool = True


@dataclass(frozen=True)
class EditarEscalaoAreaData:
    """Input data for editing a machine area tier."""

    nivel: int = 1
    area_max_m2: Decimal | None = None
    preco_peca_std: Decimal | None = None
    preco_peca_serie: Decimal | None = None
    ativo: bool = True


class DefMaquinaEscalaoAreaService:
    """Application service for DefMaquinaEscalaoArea workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefMaquinaEscalaoAreaRepository(session)

    def listar_escaloes_da_maquina(
        self, def_maquina_id: int
    ) -> list[DefMaquinaEscalaoAreaResumo]:
        """List all area tiers of a machine (ordered by level)."""
        return self.repository.list_by_maquina(def_maquina_id)

    def listar_escaloes_ativos_da_maquina(
        self, def_maquina_id: int
    ) -> list[DefMaquinaEscalaoAreaResumo]:
        """List active area tiers of a machine (ordered by level)."""
        return self.repository.list_active_by_maquina(def_maquina_id)

    def obter_por_id(self, id: int) -> DefMaquinaEscalaoAreaResumo | None:
        """Get one area tier by id."""
        return self.repository.get_by_id(id)

    def adicionar_escalao(
        self, data: CriarEscalaoAreaData
    ) -> DefMaquinaEscalaoAreaResumo:
        """Add an area tier to a machine."""
        def_maquina_id = self._validate_required_id(data.def_maquina_id)

        result = self.repository.create_escalao(
            def_maquina_id=def_maquina_id,
            nivel=self._normalize_nivel(data.nivel),
            area_max_m2=data.area_max_m2,
            preco_peca_std=data.preco_peca_std,
            preco_peca_serie=data.preco_peca_serie,
            ativo=data.ativo,
        )
        self.session.commit()

        return result

    def editar_escalao(
        self, id: int, data: EditarEscalaoAreaData
    ) -> DefMaquinaEscalaoAreaResumo:
        """Edit an area tier."""
        result = self.repository.update_escalao(
            id=id,
            nivel=self._normalize_nivel(data.nivel),
            area_max_m2=data.area_max_m2,
            preco_peca_std=data.preco_peca_std,
            preco_peca_serie=data.preco_peca_serie,
            ativo=data.ativo,
        )
        self.session.commit()

        return result

    def desativar_escalao(self, id: int) -> bool:
        """Deactivate an area tier."""
        deactivated = self.repository.deactivate_escalao(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_escalao(self, id: int) -> bool:
        """Reactivate an area tier."""
        activated = self.repository.activate_escalao(id)
        if activated:
            self.session.commit()

        return activated

    def _validate_required_id(self, value: int | None) -> int:
        if not value:
            raise ValueError("def_maquina_id is required")

        return value

    def _normalize_nivel(self, nivel: int | None) -> int:
        if not nivel or nivel < 1:
            return 1

        return nivel
