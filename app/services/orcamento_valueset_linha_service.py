"""Service for budget version ValueSet line workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.valueset_types import normalize_valueset_key
from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaRepository
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloRepository
from app.repositories.orcamento_valueset_linha_repository import (
    OrcamentoValuesetLinhaRepository,
    OrcamentoValuesetLinhaResumo,
)


@dataclass(frozen=True)
class CriarOrcamentoValuesetLinhaData:
    """Input data for creating one budget version ValueSet line."""

    orcamento_versao_id: int | None
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
class EditarOrcamentoValuesetLinhaData:
    """Input data for editing one budget version ValueSet line."""

    orcamento_versao_id: int | None
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
class ImportarModeloResult:
    """Summary of importing a ValueSet model into a budget version."""

    modelo_codigo: str
    criadas: int
    atualizadas: int
    ignoradas: int


class OrcamentoValuesetLinhaService:
    """Application service for budget version ValueSet lines."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoValuesetLinhaRepository(session)
        self.modelo_repository = DefValuesetModeloRepository(session)
        self.modelo_linha_repository = DefValuesetModeloLinhaRepository(session)

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

    def listar_por_chave(
        self, orcamento_versao_id: int, chave: str
    ) -> list[OrcamentoValuesetLinhaResumo]:
        """List all options of one budget version and key."""
        return self.repository.list_by_versao_chave(
            orcamento_versao_id, normalize_valueset_key(chave)
        )

    def obter_padrao_por_chave(
        self, orcamento_versao_id: int, chave: str
    ) -> OrcamentoValuesetLinhaResumo | None:
        """Get the active default option of one budget version and key."""
        return self.repository.get_default_by_versao_chave(
            orcamento_versao_id, normalize_valueset_key(chave)
        )

    def obter_por_id(self, id: int) -> OrcamentoValuesetLinhaResumo | None:
        """Get one budget version ValueSet line by id."""
        return self.repository.get_by_id(id)

    def criar_linha(
        self, data: CriarOrcamentoValuesetLinhaData
    ) -> OrcamentoValuesetLinhaResumo:
        """Create one budget version ValueSet line."""
        fields = self._build_fields(data)
        self._validate_opcao_unica(
            orcamento_versao_id=fields["orcamento_versao_id"],
            chave=fields["chave"],
            codigo_opcao=fields["codigo_opcao"],
            exclude_id=None,
        )
        self._validate_padrao_unico(
            orcamento_versao_id=fields["orcamento_versao_id"],
            chave=fields["chave"],
            padrao=fields["padrao"],
            ativo=fields["ativo"],
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
        self._validate_opcao_unica(
            orcamento_versao_id=fields["orcamento_versao_id"],
            chave=fields["chave"],
            codigo_opcao=fields["codigo_opcao"],
            exclude_id=id,
        )
        self._validate_padrao_unico(
            orcamento_versao_id=fields["orcamento_versao_id"],
            chave=fields["chave"],
            padrao=fields["padrao"],
            ativo=fields["ativo"],
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

    def definir_como_padrao(self, id: int) -> bool:
        """Make one line the default option of its key, clearing the others."""
        linha = self.repository.get_by_id(id)
        if linha is None:
            return False

        self.repository.clear_padrao_for_chave(
            linha.orcamento_versao_id, linha.chave, exclude_id=id
        )
        self.repository.set_padrao(id, True)
        self.session.commit()

        return True

    def importar_modelo_para_orcamento(
        self, orcamento_versao_id: int, def_valueset_modelo_id: int
    ) -> ImportarModeloResult:
        """Copy the active lines of a ValueSet model into a budget version.

        Existing lines (same chave + codigo_opcao) are updated when they are
        not locally edited, and kept untouched when editado_localmente is True.
        """
        modelo = self.modelo_repository.get_by_id(def_valueset_modelo_id)
        if modelo is None:
            raise ValueError("modelo nao encontrado")

        criadas = 0
        atualizadas = 0
        ignoradas = 0

        for linha in self.modelo_linha_repository.list_by_modelo(def_valueset_modelo_id):
            if not linha.ativo:
                continue

            existing = self.repository.get_by_versao_chave_opcao(
                orcamento_versao_id, linha.chave, linha.codigo_opcao
            )
            fields = self._build_import_fields(orcamento_versao_id, modelo, linha)

            if existing is None:
                self.repository.create(**fields)
                criadas += 1
            elif existing.editado_localmente:
                ignoradas += 1
            else:
                self.repository.update(id=existing.id, **fields)
                atualizadas += 1

        self.session.commit()

        return ImportarModeloResult(
            modelo_codigo=modelo.codigo,
            criadas=criadas,
            atualizadas=atualizadas,
            ignoradas=ignoradas,
        )

    def _build_import_fields(self, orcamento_versao_id: int, modelo, linha) -> dict:
        return {
            "orcamento_versao_id": orcamento_versao_id,
            "chave": linha.chave,
            "codigo_opcao": linha.codigo_opcao,
            "nome_opcao": linha.nome_opcao,
            "padrao": linha.padrao,
            "ordem": linha.ordem,
            "descricao": linha.descricao,
            "materia_prima_id": linha.materia_prima_id,
            "ref_materia_prima": linha.ref_materia_prima,
            "descricao_materia_prima": linha.descricao_materia_prima,
            "valor_texto": linha.valor_texto,
            "origem": linha.origem,
            "ref_le": linha.ref_le,
            "descricao_no_orcamento": linha.descricao_no_orcamento,
            "preco_tabela": linha.preco_tabela,
            "margem_percentagem": linha.margem_percentagem,
            "desconto_percentagem": linha.desconto_percentagem,
            "preco_liquido": linha.preco_liquido,
            "unidade": linha.unidade,
            "desperdicio_percentagem": linha.desperdicio_percentagem,
            "tipo_materia_prima": linha.tipo_materia_prima,
            "familia_materia_prima": linha.familia_materia_prima,
            "coresp_orla_0_4": linha.coresp_orla_0_4,
            "coresp_orla_1_0": linha.coresp_orla_1_0,
            "comp_mp": linha.comp_mp,
            "larg_mp": linha.larg_mp,
            "esp_mp": linha.esp_mp,
            "origem_dados": "MODELO_VALUESET",
            "origem_modelo_id": modelo.id,
            "origem_modelo_codigo": modelo.codigo,
            "editado_localmente": False,
            "ativo": True,
            "observacoes": linha.observacoes,
        }

    def _build_fields(self, data) -> dict:
        orcamento_versao_id = self._validate_required_id(
            data.orcamento_versao_id, "orcamento_versao_id"
        )
        chave = self._normalize_required_chave(data.chave)

        return {
            "orcamento_versao_id": orcamento_versao_id,
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
        self,
        orcamento_versao_id: int,
        chave: str,
        codigo_opcao: str,
        exclude_id: int | None,
    ) -> None:
        existing = self.repository.get_by_versao_chave_opcao(
            orcamento_versao_id, chave, codigo_opcao
        )
        if existing is not None and existing.id != exclude_id:
            raise ValueError("opcao ja existe nesta chave desta versao")

    def _validate_padrao_unico(
        self,
        orcamento_versao_id: int,
        chave: str,
        padrao: bool,
        ativo: bool,
        exclude_id: int | None,
    ) -> None:
        if not (padrao and ativo):
            return

        existing = self.repository.get_default_by_versao_chave(orcamento_versao_id, chave)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("ja existe uma opcao padrao para esta chave")
