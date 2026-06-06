"""Service for budget version ValueSet line workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.valueset_types import normalize_valueset_key
from app.repositories.orcamento_valueset_linha_repository import (
    OrcamentoValuesetLinhaRepository,
    OrcamentoValuesetLinhaResumo,
)


@dataclass(frozen=True)
class CriarOrcamentoValuesetLinhaData:
    """Input data for creating one budget version ValueSet line."""

    orcamento_versao_id: int | None
    chave: str
    descricao: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    valor_texto: str | None = None
    origem: str | None = None
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarOrcamentoValuesetLinhaData:
    """Input data for editing one budget version ValueSet line."""

    orcamento_versao_id: int | None
    chave: str
    descricao: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    valor_texto: str | None = None
    origem: str | None = None
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


class OrcamentoValuesetLinhaService:
    """Application service for budget version ValueSet lines."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoValuesetLinhaRepository(session)

    def listar_linhas(self) -> list[OrcamentoValuesetLinhaResumo]:
        """List all budget version ValueSet lines."""
        return self.repository.list_all()

    def listar_linhas_ativas(self) -> list[OrcamentoValuesetLinhaResumo]:
        """List active budget version ValueSet lines."""
        return self.repository.list_active()

    def listar_linhas_da_versao(
        self, orcamento_versao_id: int
    ) -> list[OrcamentoValuesetLinhaResumo]:
        """List ValueSet lines of one budget version."""
        return self.repository.list_by_orcamento_versao(orcamento_versao_id)

    def obter_por_id(self, id: int) -> OrcamentoValuesetLinhaResumo | None:
        """Get one budget version ValueSet line by id."""
        return self.repository.get_by_id(id)

    def criar_linha(
        self, data: CriarOrcamentoValuesetLinhaData
    ) -> OrcamentoValuesetLinhaResumo:
        """Create one budget version ValueSet line."""
        fields = self._build_fields(data)
        self._validate_chave_unica(
            orcamento_versao_id=fields["orcamento_versao_id"],
            chave=fields["chave"],
            exclude_id=None,
        )

        result = self.repository.create(**fields)
        self.session.commit()

        return result

    def editar_linha(
        self, id: int, data: EditarOrcamentoValuesetLinhaData
    ) -> OrcamentoValuesetLinhaResumo:
        """Edit one budget version ValueSet line."""
        fields = self._build_fields(data)
        self._validate_chave_unica(
            orcamento_versao_id=fields["orcamento_versao_id"],
            chave=fields["chave"],
            exclude_id=id,
        )

        result = self.repository.update(id=id, **fields)
        self.session.commit()

        return result

    def desativar_linha(self, id: int) -> bool:
        """Deactivate one budget version ValueSet line."""
        deactivated = self.repository.deactivate(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_linha(self, id: int) -> bool:
        """Reactivate one budget version ValueSet line."""
        activated = self.repository.activate(id)
        if activated:
            self.session.commit()

        return activated

    def _build_fields(self, data) -> dict:
        orcamento_versao_id = self._validate_required_id(
            data.orcamento_versao_id, "orcamento_versao_id"
        )
        chave = self._normalize_required_chave(data.chave)

        return {
            "orcamento_versao_id": orcamento_versao_id,
            "chave": chave,
            "descricao": data.descricao,
            "materia_prima_id": data.materia_prima_id,
            "ref_materia_prima": data.ref_materia_prima,
            "descricao_materia_prima": data.descricao_materia_prima,
            "valor_texto": data.valor_texto,
            "origem": data.origem,
            "editado_localmente": data.editado_localmente,
            "ativo": data.ativo,
            "observacoes": data.observacoes,
        }

    def _validate_required_id(self, value: int | None, field_name: str) -> int:
        if not value:
            raise ValueError(f"{field_name} is required")

        return value

    def _normalize_required_chave(self, value: str | None) -> str:
        if value is None or not value.strip():
            raise ValueError("chave is required")

        return normalize_valueset_key(value)

    def _validate_chave_unica(
        self, orcamento_versao_id: int, chave: str, exclude_id: int | None
    ) -> None:
        existing = self.repository.get_by_versao_chave(orcamento_versao_id, chave)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("chave ja existe nesta versao")
