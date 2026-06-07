"""Repository for configurable ValueSet key reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefValuesetChave


@dataclass(frozen=True)
class DefValuesetChaveResumo:
    """Read model for configurable ValueSet keys."""

    id: int
    codigo: str
    nome: str
    descricao: str | None
    tipo: str | None
    grupo: str | None
    sistema: bool
    ativo: bool
    ordem: int
    observacoes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefValuesetChaveRepository:
    """Repository for DefValuesetChave operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefValuesetChaveResumo]:
        """List all ValueSet keys."""
        statement = select(DefValuesetChave).order_by(
            DefValuesetChave.grupo.asc(),
            DefValuesetChave.ordem.asc(),
            DefValuesetChave.codigo.asc(),
        )
        chaves = self.session.execute(statement).scalars().all()

        return [self._to_resumo(chave) for chave in chaves]

    def list_active(self) -> list[DefValuesetChaveResumo]:
        """List active ValueSet keys."""
        statement = (
            select(DefValuesetChave)
            .where(DefValuesetChave.ativo.is_(True))
            .order_by(
                DefValuesetChave.grupo.asc(),
                DefValuesetChave.ordem.asc(),
                DefValuesetChave.codigo.asc(),
            )
        )
        chaves = self.session.execute(statement).scalars().all()

        return [self._to_resumo(chave) for chave in chaves]

    def list_by_tipo(self, tipo: str) -> list[DefValuesetChaveResumo]:
        """List ValueSet keys of one type."""
        statement = (
            select(DefValuesetChave)
            .where(DefValuesetChave.tipo == tipo)
            .order_by(
                DefValuesetChave.grupo.asc(),
                DefValuesetChave.ordem.asc(),
                DefValuesetChave.codigo.asc(),
            )
        )
        chaves = self.session.execute(statement).scalars().all()

        return [self._to_resumo(chave) for chave in chaves]

    def get_by_id(self, id: int) -> DefValuesetChaveResumo | None:
        """Get one ValueSet key by id."""
        chave = self.session.get(DefValuesetChave, id)
        if chave is None:
            return None

        return self._to_resumo(chave)

    def get_by_codigo(self, codigo: str) -> DefValuesetChaveResumo | None:
        """Get one ValueSet key by code."""
        statement = select(DefValuesetChave).where(DefValuesetChave.codigo == codigo)
        chave = self.session.execute(statement).scalars().first()
        if chave is None:
            return None

        return self._to_resumo(chave)

    def create_chave(
        self,
        *,
        codigo: str,
        nome: str,
        descricao: str | None = None,
        tipo: str | None = None,
        grupo: str | None = None,
        sistema: bool = False,
        ativo: bool = True,
        ordem: int = 1,
        observacoes: str | None = None,
    ) -> DefValuesetChaveResumo:
        """Create one ValueSet key."""
        chave = DefValuesetChave(
            codigo=codigo,
            nome=nome,
            descricao=descricao,
            tipo=tipo,
            grupo=grupo,
            sistema=sistema,
            ativo=ativo,
            ordem=ordem,
            observacoes=observacoes,
        )
        self.session.add(chave)
        self.session.flush()

        return self._to_resumo(chave)

    def update_chave(
        self,
        *,
        id: int,
        codigo: str,
        nome: str,
        descricao: str | None = None,
        tipo: str | None = None,
        grupo: str | None = None,
        sistema: bool = False,
        ativo: bool = True,
        ordem: int = 1,
        observacoes: str | None = None,
    ) -> DefValuesetChaveResumo:
        """Update one ValueSet key."""
        chave = self.session.get(DefValuesetChave, id)
        if chave is None:
            raise ValueError("def_valueset_chave not found")

        chave.codigo = codigo
        chave.nome = nome
        chave.descricao = descricao
        chave.tipo = tipo
        chave.grupo = grupo
        chave.sistema = sistema
        chave.ativo = ativo
        chave.ordem = ordem
        chave.observacoes = observacoes
        self.session.flush()

        return self._to_resumo(chave)

    def deactivate_chave(self, id: int) -> bool:
        """Deactivate one ValueSet key."""
        chave = self.session.get(DefValuesetChave, id)
        if chave is None:
            return False

        chave.ativo = False
        self.session.flush()

        return True

    def activate_chave(self, id: int) -> bool:
        """Reactivate one ValueSet key."""
        chave = self.session.get(DefValuesetChave, id)
        if chave is None:
            return False

        chave.ativo = True
        self.session.flush()

        return True

    def _to_resumo(self, chave: DefValuesetChave) -> DefValuesetChaveResumo:
        """Convert an ORM ValueSet key to the read model."""
        return DefValuesetChaveResumo(
            id=chave.id,
            codigo=chave.codigo,
            nome=chave.nome,
            descricao=chave.descricao,
            tipo=chave.tipo,
            grupo=chave.grupo,
            sistema=chave.sistema,
            ativo=chave.ativo,
            ordem=chave.ordem,
            observacoes=chave.observacoes,
            created_at=chave.created_at,
            updated_at=chave.updated_at,
        )
