"""Service for reusable ValueSet model workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories.def_valueset_modelo_repository import (
    DefValuesetModeloRepository,
    DefValuesetModeloResumo,
)


@dataclass(frozen=True)
class CriarDefValuesetModeloData:
    """Input data for creating a reusable ValueSet model."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    ambito: str = "UTILIZADOR"
    user_id: int | None = None
    visivel_para_todos: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarDefValuesetModeloData:
    """Input data for editing a reusable ValueSet model."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    ambito: str = "UTILIZADOR"
    user_id: int | None = None
    visivel_para_todos: bool = False
    ativo: bool = True
    observacoes: str | None = None


class DefValuesetModeloService:
    """Application service for reusable ValueSet models."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefValuesetModeloRepository(session)

    def listar_modelos(self) -> list[DefValuesetModeloResumo]:
        """List all reusable ValueSet models."""
        return self.repository.list_all()

    def listar_modelos_ativos(self) -> list[DefValuesetModeloResumo]:
        """List active reusable ValueSet models."""
        return self.repository.list_active()

    def listar_modelos_utilizador(self) -> list[DefValuesetModeloResumo]:
        """List active models scoped to the user (not global / not shared)."""
        return [
            modelo
            for modelo in self.repository.list_active()
            if not self._e_global(modelo)
        ]

    def listar_modelos_globais(self) -> list[DefValuesetModeloResumo]:
        """List active models that are global or shared with everyone."""
        return [
            modelo
            for modelo in self.repository.list_active()
            if self._e_global(modelo)
        ]

    def _e_global(self, modelo: DefValuesetModeloResumo) -> bool:
        ambito = (modelo.ambito or "").strip().upper()
        return ambito == "GLOBAL" or bool(modelo.visivel_para_todos)

    def obter_por_id(self, id: int) -> DefValuesetModeloResumo | None:
        """Get one reusable ValueSet model by id."""
        return self.repository.get_by_id(id)

    def obter_por_codigo(self, codigo: str | None) -> DefValuesetModeloResumo | None:
        """Get one reusable ValueSet model by code."""
        normalized = self._normalize_optional_text(codigo)
        if normalized is None:
            return None

        return self.repository.get_by_codigo(normalized)

    def criar_modelo(self, data: CriarDefValuesetModeloData) -> DefValuesetModeloResumo:
        """Create one reusable ValueSet model."""
        fields = self._build_fields(data)
        self._validate_codigo_unico(fields["codigo"], exclude_id=None)

        result = self.repository.create(**fields)
        self.session.commit()

        return result

    def editar_modelo(
        self, id: int, data: EditarDefValuesetModeloData
    ) -> DefValuesetModeloResumo:
        """Edit one reusable ValueSet model."""
        fields = self._build_fields(data)
        self._validate_codigo_unico(fields["codigo"], exclude_id=id)

        result = self.repository.update(id=id, **fields)
        self.session.commit()

        return result

    def desativar_modelo(self, id: int) -> bool:
        """Deactivate one reusable ValueSet model."""
        deactivated = self.repository.deactivate(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_modelo(self, id: int) -> bool:
        """Reactivate one reusable ValueSet model."""
        activated = self.repository.activate(id)
        if activated:
            self.session.commit()

        return activated

    def _build_fields(self, data) -> dict:
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")

        return {
            "codigo": codigo,
            "nome": nome,
            "descricao": data.descricao,
            "tipo": self._normalize_optional_text(data.tipo),
            "ambito": self._normalize_ambito(data.ambito),
            "user_id": data.user_id,
            "visivel_para_todos": data.visivel_para_todos,
            "ativo": data.ativo,
            "observacoes": data.observacoes,
        }

    def _normalize_codigo(self, codigo: str | None) -> str:
        normalized = (codigo or "").strip().upper()
        if not normalized:
            raise ValueError("codigo is required")

        return "_".join(normalized.split())

    def _normalize_ambito(self, ambito: str | None) -> str:
        normalized = (ambito or "").strip().upper()
        return normalized or "UTILIZADOR"

    def _normalize_required_text(self, value: str | None, field_name: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} is required")

        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    def _validate_codigo_unico(self, codigo: str, exclude_id: int | None) -> None:
        existing = self.repository.get_by_codigo(codigo)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("codigo ja existe")
