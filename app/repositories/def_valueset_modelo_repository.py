"""Repository for reusable ValueSet models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import DefValuesetModelo


@dataclass(frozen=True)
class DefValuesetModeloResumo:
    """Read model for reusable ValueSet models."""

    id: int
    codigo: str
    nome: str
    descricao: str | None
    tipo: str | None
    ambito: str
    user_id: int | None
    visivel_para_todos: bool
    ativo: bool
    observacoes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    owner_username: str | None = None


class DefValuesetModeloRepository:
    """Repository for DefValuesetModelo operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefValuesetModeloResumo]:
        """List all reusable ValueSet models."""
        statement = (
            select(DefValuesetModelo)
            .options(joinedload(DefValuesetModelo.user))
            .order_by(DefValuesetModelo.codigo.asc(), DefValuesetModelo.id.asc())
        )
        modelos = self.session.execute(statement).scalars().all()

        return [self._to_resumo(modelo) for modelo in modelos]

    def list_active(self) -> list[DefValuesetModeloResumo]:
        """List active reusable ValueSet models."""
        statement = (
            select(DefValuesetModelo)
            .options(joinedload(DefValuesetModelo.user))
            .where(DefValuesetModelo.ativo.is_(True))
            .order_by(DefValuesetModelo.codigo.asc(), DefValuesetModelo.id.asc())
        )
        modelos = self.session.execute(statement).scalars().all()

        return [self._to_resumo(modelo) for modelo in modelos]

    def get_by_id(self, id: int) -> DefValuesetModeloResumo | None:
        """Get one reusable ValueSet model by id."""
        modelo = self.session.get(DefValuesetModelo, id)
        if modelo is None:
            return None

        return self._to_resumo(modelo)

    def get_by_codigo(self, codigo: str) -> DefValuesetModeloResumo | None:
        """Get one reusable ValueSet model by code."""
        statement = select(DefValuesetModelo).where(DefValuesetModelo.codigo == codigo)
        modelo = self.session.execute(statement).scalars().first()
        if modelo is None:
            return None

        return self._to_resumo(modelo)

    def create(self, **fields) -> DefValuesetModeloResumo:
        """Create one reusable ValueSet model."""
        modelo = DefValuesetModelo(**fields)
        self.session.add(modelo)
        self.session.flush()

        return self._to_resumo(modelo)

    def update(self, *, id: int, **fields) -> DefValuesetModeloResumo:
        """Update one reusable ValueSet model."""
        modelo = self.session.get(DefValuesetModelo, id)
        if modelo is None:
            raise ValueError("def_valueset_modelo not found")

        for name, value in fields.items():
            setattr(modelo, name, value)
        self.session.flush()

        return self._to_resumo(modelo)

    def deactivate(self, id: int) -> bool:
        """Deactivate one reusable ValueSet model."""
        modelo = self.session.get(DefValuesetModelo, id)
        if modelo is None:
            return False

        modelo.ativo = False
        self.session.flush()

        return True

    def activate(self, id: int) -> bool:
        """Reactivate one reusable ValueSet model."""
        modelo = self.session.get(DefValuesetModelo, id)
        if modelo is None:
            return False

        modelo.ativo = True
        self.session.flush()

        return True

    def _to_resumo(self, modelo: DefValuesetModelo) -> DefValuesetModeloResumo:
        """Convert an ORM model to the read model."""
        return DefValuesetModeloResumo(
            id=modelo.id,
            codigo=modelo.codigo,
            nome=modelo.nome,
            descricao=modelo.descricao,
            tipo=modelo.tipo,
            ambito=modelo.ambito,
            user_id=modelo.user_id,
            visivel_para_todos=modelo.visivel_para_todos,
            ativo=modelo.ativo,
            observacoes=modelo.observacoes,
            created_at=modelo.created_at,
            updated_at=modelo.updated_at,
            owner_username=modelo.user.username if modelo.user is not None else None,
        )
