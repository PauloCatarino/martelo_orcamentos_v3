"""Service for budget item ValueSet line workflows."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.valueset_precos import calcular_preco_liquido
from app.domain.valueset_types import normalize_valueset_key
from app.models import OrcamentoItem
from app.repositories.def_valueset_modelo_linha_operacao_repository import (
    DefValuesetModeloLinhaOperacaoRepository,
)
from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaRepository
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloRepository
from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaRepository,
    OrcamentoItemValuesetLinhaResumo,
)
from app.repositories.orcamento_valueset_linha_operacao_repository import (
    OrcamentoValuesetLinhaOperacaoRepository,
)
from app.repositories.orcamento_valueset_linha_repository import (
    OrcamentoValuesetLinhaRepository,
    OrcamentoValuesetLinhaResumo,
)
from app.services.orcamento_item_valueset_linha_operacao_service import (
    OrcamentoItemValuesetLinhaOperacaoService,
)

# Materia-prima snapshot fields that can be edited, copied, pasted and cleared
# on an item ValueSet line (its key/option/order/active state are preserved).
SNAPSHOT_FIELDS = (
    "ref_le",
    "descricao_no_orcamento",
    "ref_materia_prima",
    "descricao_materia_prima",
    "valor_texto",
    "preco_tabela",
    "margem_percentagem",
    "desconto_percentagem",
    "preco_liquido",
    "unidade",
    "desperdicio_percentagem",
    "tipo_materia_prima",
    "familia_materia_prima",
    "coresp_orla_0_4",
    "coresp_orla_1_0",
    "comp_mp",
    "larg_mp",
    "esp_mp",
)


@dataclass(frozen=True)
class CriarOrcamentoItemValuesetLinhaData:
    """Input data for creating one budget item ValueSet line."""

    orcamento_item_id: int | None
    chave: str
    codigo_opcao: str | None = None
    nome_opcao: str | None = None
    padrao: bool = False
    prioridade: int | None = None
    ordem: int = 1
    descricao: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    valor_texto: str | None = None
    origem: str | None = None
    ref_le: str | None = None
    descricao_no_orcamento: str | None = None
    preco_tabela: Decimal | None = None
    margem_percentagem: Decimal | None = None
    desconto_percentagem: Decimal | None = None
    preco_liquido: Decimal | None = None
    unidade: str | None = None
    desperdicio_percentagem: Decimal | None = None
    tipo_materia_prima: str | None = None
    familia_materia_prima: str | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    preco_orla_0_4_m2: Decimal | None = None
    preco_orla_1_0_m2: Decimal | None = None
    comp_mp: Decimal | None = None
    larg_mp: Decimal | None = None
    esp_mp: Decimal | None = None
    origem_dados: str | None = None
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
    prioridade: int | None = None
    ordem: int = 1
    descricao: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    valor_texto: str | None = None
    origem: str | None = None
    ref_le: str | None = None
    descricao_no_orcamento: str | None = None
    preco_tabela: Decimal | None = None
    margem_percentagem: Decimal | None = None
    desconto_percentagem: Decimal | None = None
    preco_liquido: Decimal | None = None
    unidade: str | None = None
    desperdicio_percentagem: Decimal | None = None
    tipo_materia_prima: str | None = None
    familia_materia_prima: str | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    preco_orla_0_4_m2: Decimal | None = None
    preco_orla_1_0_m2: Decimal | None = None
    comp_mp: Decimal | None = None
    larg_mp: Decimal | None = None
    esp_mp: Decimal | None = None
    origem_dados: str | None = None
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
    eliminadas: int = 0
    substituir: bool = False


@dataclass(frozen=True)
class ImportarModeloParaItemResult:
    """Summary of importing a ValueSet model into one item."""

    modelo_codigo: str
    criadas: int
    atualizadas: int
    ignoradas: int
    total_origem: int
    eliminadas: int = 0


@dataclass(frozen=True)
class SubstituirPorModeloResult:
    """Summary of replacing an item ValueSet with a ValueSet model."""

    modelo_codigo: str
    desativadas: int
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
        self.modelo_repository = DefValuesetModeloRepository(session)
        self.modelo_linha_repository = DefValuesetModeloLinhaRepository(session)
        self.modelo_linha_operacao_repository = DefValuesetModeloLinhaOperacaoRepository(session)
        self.orcamento_linha_operacao_repository = OrcamentoValuesetLinhaOperacaoRepository(
            session
        )
        self.operacao_service = OrcamentoItemValuesetLinhaOperacaoService(session)

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
        """Get the winning active option of one budget item and key."""
        return self.repository.get_default_by_item_chave(
            orcamento_item_id, normalize_valueset_key(chave)
        )

    def obter_por_id(self, id: int) -> OrcamentoItemValuesetLinhaResumo | None:
        """Get one budget item ValueSet line by id."""
        return self.repository.get_by_id(id)

    def copiar_snapshot_linha(self, id: int) -> dict:
        """Return the materia-prima snapshot of one line (key/option excluded).

        Also carries the line's prioridade so copy/paste keeps the choice rank.
        """
        linha = self.repository.get_by_id(id)
        if linha is None:
            raise ValueError("linha nao encontrada")

        snapshot = {field: getattr(linha, field) for field in SNAPSHOT_FIELDS}
        snapshot["prioridade"] = linha.prioridade
        return snapshot

    def aplicar_snapshot_linha(
        self, id: int, snapshot: dict
    ) -> OrcamentoItemValuesetLinhaResumo:
        """Apply a snapshot to one line, keeping its key, option, order and state.

        preco_liquido is recomputed and the line is flagged as locally edited.
        """
        linha = self.repository.get_by_id(id)
        if linha is None:
            raise ValueError("linha nao encontrada")

        fields = {field: snapshot.get(field) for field in SNAPSHOT_FIELDS}
        if "prioridade" in snapshot:
            fields["prioridade"] = snapshot["prioridade"]
        fields["preco_liquido"] = self._compute_preco_liquido(
            fields["preco_tabela"],
            fields["margem_percentagem"],
            fields["desconto_percentagem"],
            fields["preco_liquido"],
        )
        fields["origem_dados"] = "EDITADO_LOCALMENTE"
        fields["editado_localmente"] = True

        result = self.repository.update(id=id, **fields)
        self.session.commit()

        return result

    def limpar_snapshot_linha(
        self, id: int, *, commit: bool = True
    ) -> OrcamentoItemValuesetLinhaResumo:
        """Clear the materia-prima snapshot of one line, keeping key and option."""
        linha = self.repository.get_by_id(id)
        if linha is None:
            raise ValueError("linha nao encontrada")

        fields = {field: None for field in SNAPSHOT_FIELDS}
        fields["origem_dados"] = "EDITADO_LOCALMENTE"
        fields["editado_localmente"] = True

        result = self.repository.update(id=id, **fields)
        if commit:
            self.session.commit()

        return result

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

        result = self.repository.update(id=id, **fields)
        self.session.commit()

        return result

    def desativar_linha(self, id: int, *, commit: bool = True) -> bool:
        """Deactivate one budget item ValueSet line (marks it locally edited)."""
        linha = self.repository.get_by_id(id)
        if linha is None:
            return False

        self.repository.update(id=id, ativo=False, editado_localmente=True)
        if commit:
            self.session.commit()

        return True

    def ativar_linha(self, id: int, *, commit: bool = True) -> bool:
        """Reactivate one budget item ValueSet line (marks it locally edited)."""
        linha = self.repository.get_by_id(id)
        if linha is None:
            return False

        self.repository.update(id=id, ativo=True, editado_localmente=True)
        if commit:
            self.session.commit()

        return True

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

    def atualizar_precos_linhas(
        self, atualizacoes: Iterable[tuple[int, Decimal | None, Decimal | None]]
    ) -> int:
        """Update only table and liquid prices for the given item lines."""
        atualizadas = 0
        for linha_id, preco_tabela_novo, preco_liquido_novo in atualizacoes:
            self.repository.update(
                id=linha_id,
                preco_tabela=preco_tabela_novo,
                preco_liquido=preco_liquido_novo,
            )
            atualizadas += 1

        self.session.commit()
        return atualizadas

    def obter_valor_resolvido(
        self, orcamento_item_id: int, orcamento_versao_id: int, chave: str
    ) -> OrcamentoItemValuesetLinhaResumo | OrcamentoValuesetLinhaResumo | None:
        """Resolve a ValueSet key by priority, preferring the item over the version."""
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
        self, orcamento_item_id: int, substituir: bool = False
    ) -> CriarItemValuesetDoOrcamentoResult:
        """Copy the budget version ValueSet lines into one item's ValueSet.

        Existing item lines (same chave + codigo_opcao) are updated when not
        locally edited, and kept untouched when editado_localmente is True.
        With substituir=True, the current item table is deleted and rebuilt
        from the active budget version lines.
        """
        item = self.session.get(OrcamentoItem, orcamento_item_id)
        if item is None:
            raise ValueError("item nao encontrado")

        orcamento_versao_id = item.orcamento_versao_id

        criadas = 0
        atualizadas = 0
        ignoradas = 0
        total_origem = 0
        eliminadas = 0

        if substituir:
            eliminadas = self.repository.delete_by_orcamento_item(orcamento_item_id)

        for linha in self.orcamento_repository.list_by_orcamento_versao(orcamento_versao_id):
            if not linha.ativo:
                continue

            total_origem += 1
            fields = self._build_import_fields(orcamento_item_id, orcamento_versao_id, linha)
            origem_ops = self.orcamento_linha_operacao_repository.list_by_linha(linha.id)

            if substituir:
                criada = self.repository.create(**fields)
                self.operacao_service.copiar_operacoes_de(origem_ops, criada.id)
                criadas += 1
                continue

            existing = self.repository.get_by_item_chave_opcao(
                orcamento_item_id, linha.chave, linha.codigo_opcao
            )

            if existing is None:
                criada = self.repository.create(**fields)
                self.operacao_service.copiar_operacoes_de(origem_ops, criada.id)
                criadas += 1
            elif existing.editado_localmente:
                ignoradas += 1
            else:
                self.repository.update(id=existing.id, **fields)
                self.operacao_service.copiar_operacoes_de(origem_ops, existing.id)
                atualizadas += 1

        self.session.commit()

        return CriarItemValuesetDoOrcamentoResult(
            criadas=criadas,
            atualizadas=atualizadas,
            ignoradas=ignoradas,
            total_origem=total_origem,
            eliminadas=eliminadas,
            substituir=substituir,
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
            "prioridade": linha.prioridade,
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
            "preco_orla_0_4_m2": getattr(linha, "preco_orla_0_4_m2", None),
            "preco_orla_1_0_m2": getattr(linha, "preco_orla_1_0_m2", None),
            "comp_mp": linha.comp_mp,
            "larg_mp": linha.larg_mp,
            "esp_mp": linha.esp_mp,
            "origem_orcamento_valueset_linha_id": linha.id,
            "origem_orcamento_versao_id": orcamento_versao_id,
            "origem_modelo_id": None,
            "origem_modelo_codigo": None,
            "origem_dados": "VALUESET_ORCAMENTO",
            "herdado_do_orcamento": True,
            "editado_localmente": False,
            "ativo": True,
            "observacoes": linha.observacoes,
        }

    def importar_modelo_para_item(
        self,
        orcamento_item_id: int,
        def_valueset_modelo_id: int,
        substituir: bool = False,
    ) -> ImportarModeloParaItemResult:
        """Copy the active lines of a ValueSet model into one item's ValueSet.

        Existing item lines (same chave + codigo_opcao) are updated when not
        locally edited, and kept untouched when editado_localmente is True.
        With substituir=True, the current table is deleted and rebuilt from the
        active model lines.
        """
        item = self.session.get(OrcamentoItem, orcamento_item_id)
        if item is None:
            raise ValueError("item nao encontrado")

        modelo = self.modelo_repository.get_by_id(def_valueset_modelo_id)
        if modelo is None:
            raise ValueError("modelo nao encontrado")

        criadas = 0
        atualizadas = 0
        ignoradas = 0
        total_origem = 0
        eliminadas = 0

        if substituir:
            eliminadas = self.repository.delete_by_orcamento_item(orcamento_item_id)

        for linha in self.modelo_linha_repository.list_by_modelo(def_valueset_modelo_id):
            if not linha.ativo:
                continue

            total_origem += 1
            fields = self._build_modelo_import_fields(orcamento_item_id, modelo, linha)
            modelo_ops = self.modelo_linha_operacao_repository.list_by_linha(linha.id)

            if substituir:
                criada = self.repository.create(**fields)
                self.operacao_service.copiar_operacoes_de(modelo_ops, criada.id)
                criadas += 1
                continue

            existing = self.repository.get_by_item_chave_opcao(
                orcamento_item_id, linha.chave, linha.codigo_opcao
            )

            if existing is None:
                criada = self.repository.create(**fields)
                self.operacao_service.copiar_operacoes_de(modelo_ops, criada.id)
                criadas += 1
            elif existing.editado_localmente:
                ignoradas += 1
            else:
                self.repository.update(id=existing.id, **fields)
                self.operacao_service.copiar_operacoes_de(modelo_ops, existing.id)
                atualizadas += 1

        self.session.commit()

        return ImportarModeloParaItemResult(
            modelo_codigo=modelo.codigo,
            criadas=criadas,
            atualizadas=atualizadas,
            ignoradas=ignoradas,
            total_origem=total_origem,
            eliminadas=eliminadas,
        )

    def substituir_por_modelo(
        self, orcamento_item_id: int, def_valueset_modelo_id: int
    ) -> SubstituirPorModeloResult:
        """Replace an item's ValueSet with a model: deactivate then import.

        Currently active lines are deactivated (kept in the table as inactive),
        and the model's active lines become the new active lines. Because the
        (item, chave, codigo_opcao) uniqueness also covers inactive rows, a
        model line that matches a just-deactivated row reactivates and
        overwrites it instead of creating a duplicate.
        """
        item = self.session.get(OrcamentoItem, orcamento_item_id)
        if item is None:
            raise ValueError("item nao encontrado")

        modelo = self.modelo_repository.get_by_id(def_valueset_modelo_id)
        if modelo is None:
            raise ValueError("modelo nao encontrado")

        desativadas = 0
        for linha in self.repository.list_active_by_orcamento_item(orcamento_item_id):
            if self.repository.deactivate(linha.id):
                desativadas += 1

        criadas = 0
        atualizadas = 0
        total_origem = 0

        for linha in self.modelo_linha_repository.list_by_modelo(def_valueset_modelo_id):
            if not linha.ativo:
                continue

            total_origem += 1
            existing = self.repository.get_by_item_chave_opcao(
                orcamento_item_id, linha.chave, linha.codigo_opcao
            )
            fields = self._build_modelo_import_fields(orcamento_item_id, modelo, linha)

            if existing is None:
                self.repository.create(**fields)
                criadas += 1
            else:
                self.repository.update(id=existing.id, **fields)
                atualizadas += 1

        self.session.commit()

        return SubstituirPorModeloResult(
            modelo_codigo=modelo.codigo,
            desativadas=desativadas,
            criadas=criadas,
            atualizadas=atualizadas,
            ignoradas=0,
            total_origem=total_origem,
        )

    def _build_modelo_import_fields(self, orcamento_item_id: int, modelo, linha) -> dict:
        return {
            "orcamento_item_id": orcamento_item_id,
            "chave": linha.chave,
            "codigo_opcao": linha.codigo_opcao,
            "nome_opcao": linha.nome_opcao,
            "padrao": linha.padrao,
            "prioridade": linha.prioridade,
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
            "origem_orcamento_valueset_linha_id": None,
            "origem_orcamento_versao_id": None,
            "origem_modelo_id": modelo.id,
            "origem_modelo_codigo": modelo.codigo,
            "origem_dados": "MODELO_VALUESET",
            "herdado_do_orcamento": False,
            "editado_localmente": False,
            "ativo": True,
            "observacoes": linha.observacoes,
        }

    def _build_fields(self, data) -> dict:
        orcamento_item_id = self._validate_required_id(
            data.orcamento_item_id, "orcamento_item_id"
        )
        chave = self._normalize_required_chave(data.chave)
        preco_liquido = self._compute_preco_liquido(
            data.preco_tabela,
            data.margem_percentagem,
            data.desconto_percentagem,
            data.preco_liquido,
        )

        return {
            "orcamento_item_id": orcamento_item_id,
            "chave": chave,
            "codigo_opcao": self._normalize_codigo_opcao(data.codigo_opcao, chave),
            "nome_opcao": data.nome_opcao,
            "padrao": data.padrao,
            "prioridade": self._normalize_prioridade(data.prioridade),
            "ordem": self._normalize_ordem(data.ordem),
            "descricao": data.descricao,
            "materia_prima_id": data.materia_prima_id,
            "ref_materia_prima": data.ref_materia_prima,
            "descricao_materia_prima": data.descricao_materia_prima,
            "valor_texto": data.valor_texto,
            "origem": data.origem,
            "ref_le": data.ref_le,
            "descricao_no_orcamento": data.descricao_no_orcamento,
            "preco_tabela": data.preco_tabela,
            "margem_percentagem": data.margem_percentagem,
            "desconto_percentagem": data.desconto_percentagem,
            "preco_liquido": preco_liquido,
            "unidade": data.unidade,
            "desperdicio_percentagem": data.desperdicio_percentagem,
            "tipo_materia_prima": data.tipo_materia_prima,
            "familia_materia_prima": data.familia_materia_prima,
            "coresp_orla_0_4": data.coresp_orla_0_4,
            "coresp_orla_1_0": data.coresp_orla_1_0,
            "preco_orla_0_4_m2": data.preco_orla_0_4_m2,
            "preco_orla_1_0_m2": data.preco_orla_1_0_m2,
            "comp_mp": data.comp_mp,
            "larg_mp": data.larg_mp,
            "esp_mp": data.esp_mp,
            "origem_dados": data.origem_dados,
            "herdado_do_orcamento": data.herdado_do_orcamento,
            "editado_localmente": data.editado_localmente,
            "ativo": data.ativo,
            "observacoes": data.observacoes,
        }

    def _compute_preco_liquido(
        self,
        preco_tabela: Decimal | None,
        margem: Decimal | None,
        desconto: Decimal | None,
        preco_liquido: Decimal | None,
    ) -> Decimal | None:
        """preco_liquido = preco_tabela * (1 - desconto/100) * (1 + margem/100).

        Recomputed whenever a table price exists (empty margin/discount are
        treated as 0). Without a table price, the provided value is kept.
        """
        if preco_tabela is None:
            return preco_liquido

        return calcular_preco_liquido(preco_tabela, margem, desconto)

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

    def _normalize_prioridade(self, prioridade: int | None) -> int | None:
        if prioridade is None:
            return None
        if prioridade < 1:
            raise ValueError("prioridade deve ser um inteiro >= 1")

        return prioridade

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
