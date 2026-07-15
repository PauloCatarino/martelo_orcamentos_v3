"""Service for budget version ValueSet line workflows."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.valueset_precos import calcular_preco_liquido
from app.domain.valueset_opcoes import base_codigo_opcao
from app.domain.valueset_types import normalize_valueset_key
from app.repositories.def_valueset_modelo_linha_operacao_repository import (
    DefValuesetModeloLinhaOperacaoRepository,
)
from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaRepository
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloRepository
from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaRepository,
)
from app.repositories.orcamento_valueset_linha_repository import (
    OrcamentoValuesetLinhaRepository,
    OrcamentoValuesetLinhaResumo,
)
from app.services.orcamento_valueset_linha_operacao_service import (
    OrcamentoValuesetLinhaOperacaoService,
)

# Materia-prima snapshot fields that can be copied, pasted and cleared between
# budget ValueSet lines (their key/option/order/active state is preserved).
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
class CriarOrcamentoValuesetLinhaData:
    """Input data for creating one budget version ValueSet line."""

    orcamento_versao_id: int | None
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
    origem_modelo_id: int | None = None
    origem_modelo_codigo: str | None = None
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
    origem_modelo_id: int | None = None
    origem_modelo_codigo: str | None = None
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
    eliminadas: int = 0


class OrcamentoValuesetLinhaService:
    """Application service for budget version ValueSet lines."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoValuesetLinhaRepository(session)
        self.item_valueset_repository = OrcamentoItemValuesetLinhaRepository(session)
        self.modelo_repository = DefValuesetModeloRepository(session)
        self.modelo_linha_repository = DefValuesetModeloLinhaRepository(session)
        self.modelo_linha_operacao_repository = DefValuesetModeloLinhaOperacaoRepository(session)
        self.operacao_service = OrcamentoValuesetLinhaOperacaoService(session)

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
        """Get the winning active option of one budget version and key."""
        return self.repository.get_default_by_versao_chave(
            orcamento_versao_id, normalize_valueset_key(chave)
        )

    def obter_por_id(self, id: int) -> OrcamentoValuesetLinhaResumo | None:
        """Get one budget version ValueSet line by id."""
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
    ) -> OrcamentoValuesetLinhaResumo:
        """Apply a snapshot to one line, keeping its key, option, order and state.

        preco_liquido is recomputed from the pasted table price, margin and
        discount. The line is flagged as locally edited.
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
    ) -> OrcamentoValuesetLinhaResumo:
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

        result = self.repository.create(**fields)
        self.session.commit()

        return result

    def editar_linha(
        self, id: int, data: EditarOrcamentoValuesetLinhaData
    ) -> OrcamentoValuesetLinhaResumo:
        """Edit one budget version ValueSet line."""
        existing = self.repository.get_by_id(id)
        if existing is None:
            raise ValueError("linha nao encontrada")

        # The technical identity is immutable from the friendly-name dialog.
        fields = self._build_fields(data, codigo_opcao_original=existing.codigo_opcao)
        self._validate_opcao_unica(
            orcamento_versao_id=fields["orcamento_versao_id"],
            chave=fields["chave"],
            codigo_opcao=fields["codigo_opcao"],
            exclude_id=id,
        )

        result = self.repository.update(id=id, **fields)
        self.session.commit()

        return result

    def desativar_linha(self, id: int, *, commit: bool = True) -> bool:
        """Deactivate one budget version ValueSet line."""
        deactivated = self.repository.deactivate(id)
        if deactivated and commit:
            self.session.commit()

        return deactivated

    def ativar_linha(self, id: int, *, commit: bool = True) -> bool:
        """Reactivate one budget version ValueSet line."""
        activated = self.repository.activate(id)
        if activated and commit:
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

    def atualizar_precos_linhas(
        self, atualizacoes: Iterable[tuple[int, Decimal | None, Decimal | None]]
    ) -> int:
        """Update only table and liquid prices for the given budget lines."""
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

    def importar_modelo_para_orcamento(
        self,
        orcamento_versao_id: int,
        def_valueset_modelo_id: int,
        substituir: bool = False,
    ) -> ImportarModeloResult:
        """Copy the active lines of a ValueSet model into a budget version.

        Existing lines (same chave + codigo_opcao) are updated when they are
        not locally edited, and kept untouched when editado_localmente is True.
        With substituir=True, the current table is deleted and rebuilt from the
        active model lines.
        """
        modelo = self.modelo_repository.get_by_id(def_valueset_modelo_id)
        if modelo is None:
            raise ValueError("modelo nao encontrado")

        criadas = 0
        atualizadas = 0
        ignoradas = 0
        eliminadas = 0

        if substituir:
            self.item_valueset_repository.clear_origem_orcamento_valueset_for_versao(
                orcamento_versao_id
            )
            eliminadas = self.repository.delete_by_orcamento_versao(orcamento_versao_id)

        for linha in self.modelo_linha_repository.list_by_modelo(def_valueset_modelo_id):
            if not linha.ativo:
                continue

            fields = self._build_import_fields(orcamento_versao_id, modelo, linha)
            modelo_ops = self.modelo_linha_operacao_repository.list_by_linha(linha.id)

            if substituir:
                criada = self.repository.create(**fields)
                self.operacao_service.copiar_operacoes_de(modelo_ops, criada.id)
                criadas += 1
                continue

            existing = self.repository.get_by_versao_chave_opcao(
                orcamento_versao_id, linha.chave, linha.codigo_opcao
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

        return ImportarModeloResult(
            modelo_codigo=modelo.codigo,
            criadas=criadas,
            atualizadas=atualizadas,
            ignoradas=ignoradas,
            eliminadas=eliminadas,
        )

    def _build_import_fields(self, orcamento_versao_id: int, modelo, linha) -> dict:
        return {
            "orcamento_versao_id": orcamento_versao_id,
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
            "origem_dados": "MODELO_VALUESET",
            "origem_modelo_id": modelo.id,
            "origem_modelo_codigo": modelo.codigo,
            "editado_localmente": False,
            "ativo": True,
            "observacoes": linha.observacoes,
        }

    def _build_fields(self, data, *, codigo_opcao_original: str | None = None) -> dict:
        orcamento_versao_id = self._validate_required_id(
            data.orcamento_versao_id, "orcamento_versao_id"
        )
        chave = self._normalize_required_chave(data.chave)
        preco_liquido = self._compute_preco_liquido(
            data.preco_tabela,
            data.margem_percentagem,
            data.desconto_percentagem,
            data.preco_liquido,
        )

        codigo_opcao = self._resolver_codigo_opcao(
            data,
            chave=chave,
            codigo_opcao_original=codigo_opcao_original,
            orcamento_versao_id=orcamento_versao_id,
        )

        return {
            "orcamento_versao_id": orcamento_versao_id,
            "chave": chave,
            "codigo_opcao": codigo_opcao,
            "nome_opcao": self._normalize_nome_opcao(data.nome_opcao),
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
            "origem_modelo_id": data.origem_modelo_id,
            "origem_modelo_codigo": data.origem_modelo_codigo,
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

        When a table price exists, it is always recomputed (empty margin and
        discount are treated as 0). Without a table price, the provided value
        is kept.
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

    def _normalize_nome_opcao(self, nome_opcao: str | None) -> str | None:
        texto = (nome_opcao or "").strip()
        return texto or None

    def _resolver_codigo_opcao(
        self,
        data,
        *,
        chave: str,
        codigo_opcao_original: str | None,
        orcamento_versao_id: int,
    ) -> str:
        if codigo_opcao_original:
            return codigo_opcao_original

        codigo_interno = (data.codigo_opcao or "").strip()
        if codigo_interno:
            return self._normalize_codigo_opcao(codigo_interno, chave)

        base = base_codigo_opcao(
            chave=chave,
            nome_opcao=data.nome_opcao,
            ref_le=data.ref_le,
            ref_materia_prima=data.ref_materia_prima,
        )
        return self._codigo_disponivel(orcamento_versao_id, chave, base)

    def _codigo_disponivel(
        self, orcamento_versao_id: int, chave: str, base: str
    ) -> str:
        candidato = base
        sufixo = 2
        while self.repository.get_by_versao_chave_opcao(
            orcamento_versao_id, chave, candidato
        ):
            separador = f"_{sufixo}"
            candidato = f"{base[:100 - len(separador)]}{separador}"
            sufixo += 1
        return candidato

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
