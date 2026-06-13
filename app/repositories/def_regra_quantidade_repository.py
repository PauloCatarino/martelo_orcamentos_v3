"""Repository for configurable quantity rules (phase 8T.5.0)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefRegraQuantidade


@dataclass(frozen=True)
class DefRegraQuantidadeResumo:
    """Read model for a configurable quantity rule."""

    id: int
    codigo: str
    nome: str
    expressao: str
    descricao: str | None
    ativo: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefRegraQuantidadeRepository:
    """Repository for DefRegraQuantidade operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefRegraQuantidadeResumo]:
        """List every quantity rule, ordered by code."""
        statement = select(DefRegraQuantidade).order_by(
            DefRegraQuantidade.codigo.asc()
        )
        registos = self.session.execute(statement).scalars().all()

        return [self._to_resumo(registo) for registo in registos]

    def list_ativas(self) -> list[DefRegraQuantidadeResumo]:
        """List the active quantity rules, ordered by code."""
        statement = (
            select(DefRegraQuantidade)
            .where(DefRegraQuantidade.ativo.is_(True))
            .order_by(DefRegraQuantidade.codigo.asc())
        )
        registos = self.session.execute(statement).scalars().all()

        return [self._to_resumo(registo) for registo in registos]

    def get_by_id(self, id: int) -> DefRegraQuantidadeResumo | None:
        """Get one rule by id."""
        registo = self.session.get(DefRegraQuantidade, id)
        if registo is None:
            return None

        return self._to_resumo(registo)

    def get_by_codigo(self, codigo: str) -> DefRegraQuantidadeResumo | None:
        """Get one rule by its (unique) code."""
        statement = select(DefRegraQuantidade).where(
            DefRegraQuantidade.codigo == codigo
        )
        registo = self.session.execute(statement).scalars().first()
        if registo is None:
            return None

        return self._to_resumo(registo)

    def create_regra(
        self,
        *,
        codigo: str,
        nome: str,
        expressao: str,
        descricao: str | None = None,
        ativo: bool = True,
    ) -> DefRegraQuantidadeResumo:
        """Create one quantity rule."""
        registo = DefRegraQuantidade(
            codigo=codigo,
            nome=nome,
            expressao=expressao,
            descricao=descricao,
            ativo=ativo,
        )
        self.session.add(registo)
        self.session.flush()

        return self._to_resumo(registo)

    def update_regra(
        self,
        *,
        id: int,
        nome: str,
        expressao: str,
        descricao: str | None,
    ) -> DefRegraQuantidadeResumo:
        """Update the name/expression/description of one rule (code is fixed)."""
        registo = self.session.get(DefRegraQuantidade, id)
        if registo is None:
            raise ValueError("regra de quantidade nao encontrada")

        registo.nome = nome
        registo.expressao = expressao
        registo.descricao = descricao
        self.session.flush()

        return self._to_resumo(registo)

    def set_ativo(self, id: int, ativo: bool) -> DefRegraQuantidadeResumo:
        """Activate/deactivate one rule."""
        registo = self.session.get(DefRegraQuantidade, id)
        if registo is None:
            raise ValueError("regra de quantidade nao encontrada")

        registo.ativo = ativo
        self.session.flush()

        return self._to_resumo(registo)

    def _to_resumo(self, registo: DefRegraQuantidade) -> DefRegraQuantidadeResumo:
        """Convert an ORM record to the read model."""
        return DefRegraQuantidadeResumo(
            id=registo.id,
            codigo=registo.codigo,
            nome=registo.nome,
            expressao=registo.expressao,
            descricao=registo.descricao,
            ativo=registo.ativo,
            created_at=registo.created_at,
            updated_at=registo.updated_at,
        )
