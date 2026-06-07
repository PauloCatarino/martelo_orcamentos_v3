"""Service for reusable ValueSet model line workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.valueset_types import normalize_valueset_key
from app.repositories.def_valueset_modelo_linha_repository import (
    DefValuesetModeloLinhaRepository,
    DefValuesetModeloLinhaResumo,
)


@dataclass(frozen=True)
class CriarDefValuesetModeloLinhaData:
    """Input data for creating one reusable ValueSet model line."""

    def_valueset_modelo_id: int | None
    chave: str
    codigo_opcao: str | None = None
    nome_opcao: str | None = None
    padrao: bool = False
    ordem: int = 1
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
class EditarDefValuesetModeloLinhaData:
    """Input data for editing one reusable ValueSet model line."""

    def_valueset_modelo_id: int | None
    chave: str
    codigo_opcao: str | None = None
    nome_opcao: str | None = None
    padrao: bool = False
    ordem: int = 1
    descricao: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    valor_texto: str | None = None
    origem: str | None = None
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


class DefValuesetModeloLinhaService:
    """Application service for reusable ValueSet model lines."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefValuesetModeloLinhaRepository(session)

    def listar_linhas(self) -> list[DefValuesetModeloLinhaResumo]:
        """List all reusable ValueSet model lines."""
        return self.repository.list_all()

    def listar_linhas_ativas(self) -> list[DefValuesetModeloLinhaResumo]:
        """List active reusable ValueSet model lines."""
        return self.repository.list_active()

    def listar_linhas_do_modelo(
        self, modelo_id: int
    ) -> list[DefValuesetModeloLinhaResumo]:
        """List lines of one reusable ValueSet model."""
        return self.repository.list_by_modelo(modelo_id)

    def listar_por_chave(
        self, modelo_id: int, chave: str
    ) -> list[DefValuesetModeloLinhaResumo]:
        """List all options of one model and key."""
        return self.repository.list_by_modelo_chave(
            modelo_id, normalize_valueset_key(chave)
        )

    def obter_padrao_por_chave(
        self, modelo_id: int, chave: str
    ) -> DefValuesetModeloLinhaResumo | None:
        """Get the active default option of one model and key."""
        return self.repository.get_default_by_modelo_chave(
            modelo_id, normalize_valueset_key(chave)
        )

    def obter_por_id(self, id: int) -> DefValuesetModeloLinhaResumo | None:
        """Get one reusable ValueSet model line by id."""
        return self.repository.get_by_id(id)

    def criar_linha(
        self, data: CriarDefValuesetModeloLinhaData
    ) -> DefValuesetModeloLinhaResumo:
        """Create one reusable ValueSet model line."""
        fields = self._build_fields(data)
        self._validate_opcao_unica(
            modelo_id=fields["def_valueset_modelo_id"],
            chave=fields["chave"],
            codigo_opcao=fields["codigo_opcao"],
            exclude_id=None,
        )
        self._validate_padrao_unico(
            modelo_id=fields["def_valueset_modelo_id"],
            chave=fields["chave"],
            padrao=fields["padrao"],
            ativo=fields["ativo"],
            exclude_id=None,
        )

        result = self.repository.create(**fields)
        self.session.commit()

        return result

    def editar_linha(
        self, id: int, data: EditarDefValuesetModeloLinhaData
    ) -> DefValuesetModeloLinhaResumo:
        """Edit one reusable ValueSet model line."""
        fields = self._build_fields(data)
        self._validate_opcao_unica(
            modelo_id=fields["def_valueset_modelo_id"],
            chave=fields["chave"],
            codigo_opcao=fields["codigo_opcao"],
            exclude_id=id,
        )
        self._validate_padrao_unico(
            modelo_id=fields["def_valueset_modelo_id"],
            chave=fields["chave"],
            padrao=fields["padrao"],
            ativo=fields["ativo"],
            exclude_id=id,
        )

        result = self.repository.update(id=id, **fields)
        self.session.commit()

        return result

    def desativar_linha(self, id: int) -> bool:
        """Deactivate one reusable ValueSet model line."""
        deactivated = self.repository.deactivate(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_linha(self, id: int) -> bool:
        """Reactivate one reusable ValueSet model line."""
        activated = self.repository.activate(id)
        if activated:
            self.session.commit()

        return activated

    def definir_como_padrao(self, id: int) -> bool:
        """Make one line the default option of its key, clearing the others."""
        linha = self.repository.get_by_id(id)
        if linha is None:
            return False

        self.repository.clear_padrao_for_chave(
            linha.def_valueset_modelo_id, linha.chave, exclude_id=id
        )
        self.repository.set_padrao(id, True)
        self.session.commit()

        return True

    def _build_fields(self, data) -> dict:
        modelo_id = self._validate_required_id(
            data.def_valueset_modelo_id, "def_valueset_modelo_id"
        )
        chave = self._normalize_required_chave(data.chave)

        return {
            "def_valueset_modelo_id": modelo_id,
            "chave": chave,
            "codigo_opcao": self._normalize_codigo_opcao(data.codigo_opcao, chave),
            "nome_opcao": data.nome_opcao,
            "padrao": data.padrao,
            "ordem": self._normalize_ordem(data.ordem),
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

    def _normalize_codigo_opcao(self, codigo_opcao: str | None, chave: str) -> str:
        if codigo_opcao is None or not codigo_opcao.strip():
            return chave

        return codigo_opcao.strip().upper()

    def _normalize_ordem(self, ordem: int | None) -> int:
        if ordem is None:
            return 1

        return ordem

    def _validate_opcao_unica(
        self, modelo_id: int, chave: str, codigo_opcao: str, exclude_id: int | None
    ) -> None:
        existing = self.repository.get_by_modelo_chave_opcao(modelo_id, chave, codigo_opcao)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("opcao ja existe nesta chave deste modelo")

    def _validate_padrao_unico(
        self, modelo_id: int, chave: str, padrao: bool, ativo: bool, exclude_id: int | None
    ) -> None:
        if not (padrao and ativo):
            return

        existing = self.repository.get_default_by_modelo_chave(modelo_id, chave)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("ja existe uma opcao padrao para esta chave")
