"""Service for reusable piece definition workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.peca_types import normalize_peca_type
from app.repositories.def_peca_repository import DefPecaRepository, DefPecaResumo


@dataclass(frozen=True)
class CriarDefPecaData:
    """Input data for creating a reusable piece definition."""

    codigo: str
    nome: str
    descricao: str | None = None
    grupo: str | None = None
    tipo_peca: str | None = None
    ativo: bool = True


@dataclass(frozen=True)
class EditarDefPecaData:
    """Input data for editing a reusable piece definition."""

    codigo: str
    nome: str
    descricao: str | None = None
    grupo: str | None = None
    tipo_peca: str | None = None
    ativo: bool = True


class DefPecaService:
    """Application service for DefPeca workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefPecaRepository(session)

    def listar_pecas(self) -> list[DefPecaResumo]:
        """List reusable piece definitions."""
        return self.repository.list_all()

    def criar_peca(self, data: CriarDefPecaData) -> DefPecaResumo:
        """Create a reusable piece definition."""
        codigo = data.codigo.strip()
        nome = data.nome.strip()
        tipo_peca = normalize_peca_type(data.tipo_peca)
        self._validate(codigo=codigo, nome=nome)

        result = self.repository.create_def_peca(
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            grupo=data.grupo,
            tipo_peca=tipo_peca,
            ativo=data.ativo,
        )
        self.session.commit()

        return result

    def editar_peca(self, id: int, data: EditarDefPecaData) -> DefPecaResumo:
        """Edit a reusable piece definition."""
        codigo = data.codigo.strip()
        nome = data.nome.strip()
        tipo_peca = normalize_peca_type(data.tipo_peca)
        self._validate(codigo=codigo, nome=nome)

        result = self.repository.update_def_peca(
            id=id,
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            grupo=data.grupo,
            tipo_peca=tipo_peca,
            ativo=data.ativo,
        )
        self.session.commit()

        return result

    def desativar_peca(self, id: int) -> bool:
        """Deactivate a reusable piece definition."""
        deactivated = self.repository.deactivate_def_peca(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def _validate(self, *, codigo: str, nome: str) -> None:
        if not codigo:
            raise ValueError("codigo is required")

        if not nome:
            raise ValueError("nome is required")
