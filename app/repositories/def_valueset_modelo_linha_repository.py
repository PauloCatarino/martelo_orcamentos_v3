"""Repository for reusable ValueSet model lines."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefValuesetModeloLinha


@dataclass(frozen=True)
class DefValuesetModeloLinhaResumo:
    """Read model for one reusable ValueSet model line."""

    id: int
    def_valueset_modelo_id: int
    chave: str
    descricao: str | None
    materia_prima_id: int | None
    ref_materia_prima: str | None
    descricao_materia_prima: str | None
    valor_texto: str | None
    origem: str | None
    editado_localmente: bool
    ativo: bool
    observacoes: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefValuesetModeloLinhaRepository:
    """Repository for DefValuesetModeloLinha operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefValuesetModeloLinhaResumo]:
        """List all reusable ValueSet model lines."""
        statement = select(DefValuesetModeloLinha).order_by(DefValuesetModeloLinha.id.asc())
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_active(self) -> list[DefValuesetModeloLinhaResumo]:
        """List active reusable ValueSet model lines."""
        statement = (
            select(DefValuesetModeloLinha)
            .where(DefValuesetModeloLinha.ativo.is_(True))
            .order_by(DefValuesetModeloLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_by_modelo(self, modelo_id: int) -> list[DefValuesetModeloLinhaResumo]:
        """List lines of one reusable ValueSet model."""
        statement = (
            select(DefValuesetModeloLinha)
            .where(DefValuesetModeloLinha.def_valueset_modelo_id == modelo_id)
            .order_by(DefValuesetModeloLinha.chave.asc(), DefValuesetModeloLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def get_by_id(self, id: int) -> DefValuesetModeloLinhaResumo | None:
        """Get one reusable ValueSet model line by id."""
        linha = self.session.get(DefValuesetModeloLinha, id)
        if linha is None:
            return None

        return self._to_resumo(linha)

    def get_by_modelo_chave(
        self, modelo_id: int, chave: str
    ) -> DefValuesetModeloLinhaResumo | None:
        """Get one line by model and key."""
        statement = select(DefValuesetModeloLinha).where(
            DefValuesetModeloLinha.def_valueset_modelo_id == modelo_id,
            DefValuesetModeloLinha.chave == chave,
        )
        linha = self.session.execute(statement).scalars().first()
        if linha is None:
            return None

        return self._to_resumo(linha)

    def create(self, **fields) -> DefValuesetModeloLinhaResumo:
        """Create one reusable ValueSet model line."""
        linha = DefValuesetModeloLinha(**fields)
        self.session.add(linha)
        self.session.flush()

        return self._to_resumo(linha)

    def update(self, *, id: int, **fields) -> DefValuesetModeloLinhaResumo:
        """Update one reusable ValueSet model line."""
        linha = self.session.get(DefValuesetModeloLinha, id)
        if linha is None:
            raise ValueError("def_valueset_modelo_linha not found")

        for name, value in fields.items():
            setattr(linha, name, value)
        self.session.flush()

        return self._to_resumo(linha)

    def deactivate(self, id: int) -> bool:
        """Deactivate one reusable ValueSet model line."""
        linha = self.session.get(DefValuesetModeloLinha, id)
        if linha is None:
            return False

        linha.ativo = False
        self.session.flush()

        return True

    def activate(self, id: int) -> bool:
        """Reactivate one reusable ValueSet model line."""
        linha = self.session.get(DefValuesetModeloLinha, id)
        if linha is None:
            return False

        linha.ativo = True
        self.session.flush()

        return True

    def _to_resumo(self, linha: DefValuesetModeloLinha) -> DefValuesetModeloLinhaResumo:
        """Convert an ORM line to the read model."""
        return DefValuesetModeloLinhaResumo(
            id=linha.id,
            def_valueset_modelo_id=linha.def_valueset_modelo_id,
            chave=linha.chave,
            descricao=linha.descricao,
            materia_prima_id=linha.materia_prima_id,
            ref_materia_prima=linha.ref_materia_prima,
            descricao_materia_prima=linha.descricao_materia_prima,
            valor_texto=linha.valor_texto,
            origem=linha.origem,
            editado_localmente=linha.editado_localmente,
            ativo=linha.ativo,
            observacoes=linha.observacoes,
            created_at=linha.created_at,
            updated_at=linha.updated_at,
        )
