"""Service for budget item ValueSet line workflows."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.domain.valueset_types import normalize_valueset_key
from app.models import OrcamentoItem
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
    herdado_do_orcamento: bool = True
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarOrcamentoItemValuesetLinhaData:
    """Input data for editing one budget item ValueSet line."""

    orcamento_item_id: int | None
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
    herdado_do_orcamento: bool = True
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class CriarItemValuesetDoOrcamentoResult:
    """Summary of building an item ValueSet from the budget ValueSet."""

    criadas: int
    atualizadas: int
    ignoradas: int
    total_origem: int


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

    def listar_linhas_ativas_do_item(
        self, orcamento_item_id: int
    ) -> list[OrcamentoItemValuesetLinhaResumo]:
        """List active ValueSet lines of one budget item."""
        return self.repository.list_active_by_orcamento_item(orcamento_item_id)

    def listar_por_chave(
        self, orcamento_item_id: int, chave: str
    ) -> list[OrcamentoItemValuesetLinhaResumo]:
        """List all options of one budget item and key."""
        return self.repository.list_by_item_chave(
            orcamento_item_id, normalize_valueset_key(chave)
        )

    def obter_padrao_por_chave(
        self, orcamento_item_id: int, chave: str
    ) -> OrcamentoItemValuesetLinhaResumo | None:
        """Get the active default option of one budget item and key."""
        return self.repository.get_default_by_item_chave(
            orcamento_item_id, normalize_valueset_key(chave)
        )

    def obter_por_id(self, id: int) -> OrcamentoItemValuesetLinhaResumo | None:
        """Get one budget item ValueSet line by id."""
        return self.repository.get_by_id(id)

    def criar_linha(
        self, data: CriarOrcamentoItemValuesetLinhaData
    ) -> OrcamentoItemValuesetLinhaResumo:
        """Create one budget item ValueSet line."""
        fields = self._build_fields(data)
        self._validate_opcao_unica(
            orcamento_item_id=fields["orcamento_item_id"],
            chave=fields["chave"],
            codigo_opcao=fields["codigo_opcao"],
            exclude_id=None,
        )
        self._validate_padrao_unico(
            orcamento_item_id=fields["orcamento_item_id"],
            chave=fields["chave"],
            padrao=fields["padrao"],
            ativo=fields["ativo"],
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
        self._validate_opcao_unica(
            orcamento_item_id=fields["orcamento_item_id"],
            chave=fields["chave"],
            codigo_opcao=fields["codigo_opcao"],
            exclude_id=id,
        )
        self._validate_padrao_unico(
            orcamento_item_id=fields["orcamento_item_id"],
            chave=fields["chave"],
            padrao=fields["padrao"],
            ativo=fields["ativo"],
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

    def definir_como_padrao(self, id: int) -> bool:
        """Make one line the default option of its key, clearing the others."""
        linha = self.repository.get_by_id(id)
        if linha is None:
            return False

        self.repository.clear_padrao_for_chave(
            linha.orcamento_item_id, linha.chave, exclude_id=id
        )
        self.repository.set_padrao(id, True)
        self.session.commit()

        return True

    def obter_valor_resolvido(
        self, orcamento_item_id: int, orcamento_versao_id: int, chave: str
    ) -> OrcamentoItemValuesetLinhaResumo | OrcamentoValuesetLinhaResumo | None:
        """Resolve a ValueSet key default, preferring the item over the version."""
        normalized_chave = self._normalize_required_chave(chave)
        item_linha = self.repository.get_default_by_item_chave(
            orcamento_item_id, normalized_chave
        )
        if item_linha is not None:
            return item_linha

        versao_linha = self.orcamento_repository.get_default_by_versao_chave(
            orcamento_versao_id, normalized_chave
        )
        if versao_linha is not None:
            return versao_linha

        return None

    def criar_a_partir_do_orcamento(
        self, orcamento_item_id: int
    ) -> CriarItemValuesetDoOrcamentoResult:
        """Copy the budget version ValueSet lines into one item's ValueSet.

        Existing item lines (same chave + codigo_opcao) are updated when not
        locally edited, and kept untouched when editado_localmente is True.
        """
        item = self.session.get(OrcamentoItem, orcamento_item_id)
        if item is None:
            raise ValueError("item nao encontrado")

        orcamento_versao_id = item.orcamento_versao_id

        criadas = 0
        atualizadas = 0
        ignoradas = 0
        total_origem = 0

        for linha in self.orcamento_repository.list_by_orcamento_versao(orcamento_versao_id):
            if not linha.ativo:
                continue

            total_origem += 1
            existing = self.repository.get_by_item_chave_opcao(
                orcamento_item_id, linha.chave, linha.codigo_opcao
            )
            fields = self._build_import_fields(orcamento_item_id, orcamento_versao_id, linha)

            if existing is None:
                self.repository.create(**fields)
                criadas += 1
            elif existing.editado_localmente:
                ignoradas += 1
            else:
                self.repository.update(id=existing.id, **fields)
                atualizadas += 1

        self.session.commit()

        return CriarItemValuesetDoOrcamentoResult(
            criadas=criadas,
            atualizadas=atualizadas,
            ignoradas=ignoradas,
            total_origem=total_origem,
        )

    def _build_import_fields(
        self, orcamento_item_id: int, orcamento_versao_id: int, linha
    ) -> dict:
        return {
            "orcamento_item_id": orcamento_item_id,
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
            "origem_orcamento_valueset_linha_id": linha.id,
            "origem_orcamento_versao_id": orcamento_versao_id,
            "origem_dados": "VALUESET_ORCAMENTO",
            "herdado_do_orcamento": True,
            "editado_localmente": False,
            "ativo": True,
            "observacoes": linha.observacoes,
        }

    def _build_fields(self, data) -> dict:
        orcamento_item_id = self._validate_required_id(
            data.orcamento_item_id, "orcamento_item_id"
        )
        chave = self._normalize_required_chave(data.chave)

        return {
            "orcamento_item_id": orcamento_item_id,
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
        orcamento_item_id: int,
        chave: str,
        codigo_opcao: str,
        exclude_id: int | None,
    ) -> None:
        existing = self.repository.get_by_item_chave_opcao(
            orcamento_item_id, chave, codigo_opcao
        )
        if existing is not None and existing.id != exclude_id:
            raise ValueError("opcao ja existe nesta chave deste item")

    def _validate_padrao_unico(
        self,
        orcamento_item_id: int,
        chave: str,
        padrao: bool,
        ativo: bool,
        exclude_id: int | None,
    ) -> None:
        if not (padrao and ativo):
            return

        existing = self.repository.get_default_by_item_chave(orcamento_item_id, chave)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("ja existe uma opcao padrao para esta chave")
