"""Service for configurable ValueSet key workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.def_valueset_chave_repository import (
    DefValuesetChaveRepository,
    DefValuesetChaveResumo,
)


@dataclass(frozen=True)
class CriarDefValuesetChaveData:
    """Input data for creating one ValueSet key."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    grupo: str | None = None
    sistema: bool = False
    ativo: bool = True
    ordem: int = 1
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarDefValuesetChaveData:
    """Input data for editing one ValueSet key."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    grupo: str | None = None
    sistema: bool = False
    ativo: bool = True
    ordem: int = 1
    observacoes: str | None = None


class DefValuesetChaveService:
    """Application service for DefValuesetChave workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefValuesetChaveRepository(session)

    def listar_chaves(self) -> list[DefValuesetChaveResumo]:
        """List all ValueSet keys."""
        return self.repository.list_all()

    def listar_chaves_ativas(self) -> list[DefValuesetChaveResumo]:
        """List active ValueSet keys."""
        return self.repository.list_active()

    def listar_por_tipo(self, tipo: str | None) -> list[DefValuesetChaveResumo]:
        """List ValueSet keys of one type."""
        normalized = self._normalize_optional_upper(tipo)
        if normalized is None:
            return []

        return self.repository.list_by_tipo(normalized)

    def obter_por_id(self, id: int) -> DefValuesetChaveResumo | None:
        """Get one ValueSet key by id."""
        return self.repository.get_by_id(id)

    def obter_por_codigo(self, codigo: str | None) -> DefValuesetChaveResumo | None:
        """Get one ValueSet key by code."""
        normalized = self._normalize_codigo(codigo, required=False)
        if normalized is None:
            return None

        return self.repository.get_by_codigo(normalized)

    def listar_opcoes_combo(self) -> list[tuple[str, str, str | None, str | None]]:
        """Return active keys as (codigo, nome, tipo, grupo) tuples for combos."""
        return [
            (chave.codigo, chave.nome, chave.tipo, chave.grupo)
            for chave in self.repository.list_active()
        ]

    def criar_chave(self, data: CriarDefValuesetChaveData) -> DefValuesetChaveResumo:
        """Create one ValueSet key."""
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")
        self._validate_codigo_unico(codigo, exclude_id=None)

        result = self.repository.create_chave(
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            tipo=self._normalize_optional_upper(data.tipo),
            grupo=self._normalize_optional_upper(data.grupo),
            sistema=data.sistema,
            ativo=data.ativo,
            ordem=self._normalize_ordem(data.ordem),
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def editar_chave(self, id: int, data: EditarDefValuesetChaveData) -> DefValuesetChaveResumo:
        """Edit one ValueSet key."""
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")
        self._validate_codigo_unico(codigo, exclude_id=id)

        result = self.repository.update_chave(
            id=id,
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            tipo=self._normalize_optional_upper(data.tipo),
            grupo=self._normalize_optional_upper(data.grupo),
            sistema=data.sistema,
            ativo=data.ativo,
            ordem=self._normalize_ordem(data.ordem),
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def desativar_chave(self, id: int) -> bool:
        """Deactivate one ValueSet key."""
        deactivated = self.repository.deactivate_chave(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_chave(self, id: int) -> bool:
        """Reactivate one ValueSet key."""
        activated = self.repository.activate_chave(id)
        if activated:
            self.session.commit()

        return activated

    def _normalize_codigo(self, codigo: str | None, required: bool = True) -> str | None:
        normalized = (codigo or "").strip().upper()
        if not normalized:
            if required:
                raise ValueError("codigo is required")
            return None

        return "_".join(normalized.split())

    def _normalize_required_text(self, value: str | None, field_name: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} is required")

        return normalized

    def _normalize_optional_upper(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().upper()
        return normalized or None

    def _normalize_ordem(self, ordem: int | None) -> int:
        if ordem is None:
            return 1

        return ordem

    def _validate_codigo_unico(self, codigo: str, exclude_id: int | None) -> None:
        existing = self.repository.get_by_codigo(codigo)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("codigo ja existe")
