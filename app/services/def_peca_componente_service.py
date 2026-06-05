"""Service for composite piece component workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.componente_types import PECA, normalize_componente_type
from app.repositories.def_peca_componente_repository import (
    DefPecaComponenteRepository,
    DefPecaComponenteResumo,
)


@dataclass(frozen=True)
class CriarDefPecaComponenteData:
    """Input data for creating a composite piece component."""

    def_peca_pai_id: int | None
    tipo_componente: str | None = None
    def_peca_componente_id: int | None = None
    referencia_componente: str | None = None
    descricao: str | None = None
    quantidade: Decimal = Decimal("1")
    regra_quantidade: str | None = None
    obrigatorio: bool = True
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarDefPecaComponenteData:
    """Input data for editing a composite piece component."""

    def_peca_pai_id: int | None
    ordem: int
    tipo_componente: str | None = None
    def_peca_componente_id: int | None = None
    referencia_componente: str | None = None
    descricao: str | None = None
    quantidade: Decimal = Decimal("1")
    regra_quantidade: str | None = None
    obrigatorio: bool = True
    ativo: bool = True
    observacoes: str | None = None


class DefPecaComponenteService:
    """Application service for DefPecaComponente workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefPecaComponenteRepository(session)

    def listar_componentes(self, def_peca_pai_id: int) -> list[DefPecaComponenteResumo]:
        """List components for one parent piece definition."""
        return self.repository.list_by_peca_pai_id(def_peca_pai_id)

    def criar_componente(self, data: CriarDefPecaComponenteData) -> DefPecaComponenteResumo:
        """Create a composite piece component."""
        def_peca_pai_id = self._validate_parent_id(data.def_peca_pai_id)
        tipo_componente = normalize_componente_type(data.tipo_componente)
        regra_quantidade = self._normalize_regra_quantidade(data.regra_quantidade)
        self._validate_component(
            tipo_componente=tipo_componente,
            def_peca_componente_id=data.def_peca_componente_id,
            quantidade=data.quantidade,
        )

        ordem = self.repository.get_next_ordem(def_peca_pai_id)
        result = self.repository.create_componente(
            def_peca_pai_id=def_peca_pai_id,
            tipo_componente=tipo_componente,
            def_peca_componente_id=data.def_peca_componente_id,
            referencia_componente=data.referencia_componente,
            descricao=data.descricao,
            ordem=ordem,
            quantidade=data.quantidade,
            regra_quantidade=regra_quantidade,
            obrigatorio=data.obrigatorio,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def editar_componente(
        self,
        id: int,
        data: EditarDefPecaComponenteData,
    ) -> DefPecaComponenteResumo:
        """Edit a composite piece component."""
        def_peca_pai_id = self._validate_parent_id(data.def_peca_pai_id)
        tipo_componente = normalize_componente_type(data.tipo_componente)
        regra_quantidade = self._normalize_regra_quantidade(data.regra_quantidade)
        self._validate_component(
            tipo_componente=tipo_componente,
            def_peca_componente_id=data.def_peca_componente_id,
            quantidade=data.quantidade,
        )

        result = self.repository.update_componente(
            id=id,
            def_peca_pai_id=def_peca_pai_id,
            tipo_componente=tipo_componente,
            def_peca_componente_id=data.def_peca_componente_id,
            referencia_componente=data.referencia_componente,
            descricao=data.descricao,
            ordem=data.ordem,
            quantidade=data.quantidade,
            regra_quantidade=regra_quantidade,
            obrigatorio=data.obrigatorio,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def desativar_componente(self, id: int) -> bool:
        """Deactivate a composite piece component."""
        deactivated = self.repository.deactivate_componente(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def _validate_parent_id(self, def_peca_pai_id: int | None) -> int:
        if not def_peca_pai_id:
            raise ValueError("def_peca_pai_id is required")

        return def_peca_pai_id

    def _validate_component(
        self,
        *,
        tipo_componente: str,
        def_peca_componente_id: int | None,
        quantidade: Decimal,
    ) -> None:
        if quantidade <= 0:
            raise ValueError("quantidade must be greater than 0")

        if tipo_componente == PECA and not def_peca_componente_id:
            raise ValueError("def_peca_componente_id is required for PECA components")

    def _normalize_regra_quantidade(self, regra_quantidade: str | None) -> str:
        if not regra_quantidade:
            return "FIXA"

        normalized = regra_quantidade.strip()
        return normalized or "FIXA"
