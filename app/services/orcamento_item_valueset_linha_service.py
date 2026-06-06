"""Service for budget item ValueSet line workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.valueset_types import normalize_valueset_key
from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaRepository,
    OrcamentoItemValuesetLinhaResumo,
)
from app.repositories.orcamento_valueset_linha_repository import (
    OrcamentoValuesetLinhaRepository,
    OrcamentoValuesetLinhaResumo,
)


@dataclass(frozen=True)
class CriarOrcamentoItemValuesetLinhaData:
    """Input data for creating one budget item ValueSet line."""

    orcamento_item_id: int | None
    chave: str
    descricao: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    valor_texto: str | None = None
    origem: str | None = None
    herdado_do_orcamento: bool = True
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarOrcamentoItemValuesetLinhaData:
    """Input data for editing one budget item ValueSet line."""

    orcamento_item_id: int | None
    chave: str
    descricao: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    valor_texto: str | None = None
    origem: str | None = None
    herdado_do_orcamento: bool = True
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


class OrcamentoItemValuesetLinhaService:
    """Application service for budget item ValueSet lines."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoItemValuesetLinhaRepository(session)
        self.orcamento_repository = OrcamentoValuesetLinhaRepository(session)

    def listar_linhas(self) -> list[OrcamentoItemValuesetLinhaResumo]:
        """List all budget item ValueSet lines."""
        return self.repository.list_all()

    def listar_linhas_ativas(self) -> list[OrcamentoItemValuesetLinhaResumo]:
        """List active budget item ValueSet lines."""
        return self.repository.list_active()

    def listar_linhas_do_item(
        self, orcamento_item_id: int
    ) -> list[OrcamentoItemValuesetLinhaResumo]:
        """List ValueSet lines of one budget item."""
        return self.repository.list_by_orcamento_item(orcamento_item_id)

    def obter_por_id(self, id: int) -> OrcamentoItemValuesetLinhaResumo | None:
        """Get one budget item ValueSet line by id."""
        return self.repository.get_by_id(id)

    def criar_linha(
        self, data: CriarOrcamentoItemValuesetLinhaData
    ) -> OrcamentoItemValuesetLinhaResumo:
        """Create one budget item ValueSet line."""
        fields = self._build_fields(data)
        self._validate_chave_unica(
            orcamento_item_id=fields["orcamento_item_id"],
            chave=fields["chave"],
            exclude_id=None,
        )

        result = self.repository.create(**fields)
        self.session.commit()

        return result

    def editar_linha(
        self, id: int, data: EditarOrcamentoItemValuesetLinhaData
    ) -> OrcamentoItemValuesetLinhaResumo:
        """Edit one budget item ValueSet line."""
        fields = self._build_fields(data)
        self._validate_chave_unica(
            orcamento_item_id=fields["orcamento_item_id"],
            chave=fields["chave"],
            exclude_id=id,
        )

        result = self.repository.update(id=id, **fields)
        self.session.commit()

        return result

    def desativar_linha(self, id: int) -> bool:
        """Deactivate one budget item ValueSet line."""
        deactivated = self.repository.deactivate(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_linha(self, id: int) -> bool:
        """Reactivate one budget item ValueSet line."""
        activated = self.repository.activate(id)
        if activated:
            self.session.commit()

        return activated

    def obter_valor_resolvido(
        self, orcamento_item_id: int, orcamento_versao_id: int, chave: str
    ) -> OrcamentoItemValuesetLinhaResumo | OrcamentoValuesetLinhaResumo | None:
        """Resolve a ValueSet key, preferring the item over the budget version."""
        normalized_chave = self._normalize_required_chave(chave)
        item_linha = self.repository.get_by_item_chave(orcamento_item_id, normalized_chave)
        if item_linha is not None and item_linha.ativo:
            return item_linha

        versao_linha = self.orcamento_repository.get_by_versao_chave(
            orcamento_versao_id, normalized_chave
        )
        if versao_linha is not None and versao_linha.ativo:
            return versao_linha

        return None

    def _build_fields(self, data) -> dict:
        orcamento_item_id = self._validate_required_id(
            data.orcamento_item_id, "orcamento_item_id"
        )
        chave = self._normalize_required_chave(data.chave)

        return {
            "orcamento_item_id": orcamento_item_id,
            "chave": chave,
            "descricao": data.descricao,
            "materia_prima_id": data.materia_prima_id,
            "ref_materia_prima": data.ref_materia_prima,
            "descricao_materia_prima": data.descricao_materia_prima,
            "valor_texto": data.valor_texto,
            "origem": data.origem,
            "herdado_do_orcamento": data.herdado_do_orcamento,
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
        self, orcamento_item_id: int, chave: str, exclude_id: int | None
    ) -> None:
        existing = self.repository.get_by_item_chave(orcamento_item_id, chave)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("chave ja existe neste item")
