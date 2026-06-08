"""Service for budget item cost line workflows.

This phase only stores cost lines. It does not generate lines automatically
from pieces, modules or operations, and does not recompute budget totals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.custeio_linha_types import (
    MANUAL,
    PECA,
    PECA_COMPOSTA,
    normalize_custeio_linha_type,
)
from app.domain.peca_types import COMPOSTA
from app.domain.valueset_types import normalize_valueset_key
from app.repositories.def_peca_componente_repository import DefPecaComponenteRepository
from app.repositories.def_peca_repository import DefPecaRepository, DefPecaResumo
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
    OrcamentoItemCusteioLinhaResumo,
)
from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaRepository,
    OrcamentoItemValuesetLinhaResumo,
)


@dataclass(frozen=True)
class CriarLinhaCusteioData:
    """Input data for creating one cost line (manual or with a given type)."""

    orcamento_item_id: int | None
    descricao: str
    tipo_linha: str = MANUAL
    orcamento_item_modulo_id: int | None = None
    origem_tipo: str | None = None
    origem_id: int | None = None
    codigo: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    unidade: str | None = None
    quantidade: Decimal = Decimal("1")
    comp: Decimal | None = None
    larg: Decimal | None = None
    esp: Decimal | None = None
    area_m2: Decimal | None = None
    perimetro_ml: Decimal | None = None
    ml_orla_fina: Decimal | None = None
    ml_orla_grossa: Decimal | None = None
    custo_unitario: Decimal | None = None
    custo_total: Decimal | None = None
    margem_percentagem: Decimal | None = None
    preco_unitario: Decimal | None = None
    preco_total: Decimal | None = None
    def_operacao_id: int | None = None
    def_maquina_id: int | None = None
    tempo_calculado: Decimal | None = None
    tempo_manual: Decimal | None = None
    override_manual: bool = False
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarLinhaCusteioData:
    """Input data for editing one cost line."""

    orcamento_item_id: int | None
    descricao: str
    tipo_linha: str = MANUAL
    orcamento_item_modulo_id: int | None = None
    origem_tipo: str | None = None
    origem_id: int | None = None
    codigo: str | None = None
    materia_prima_id: int | None = None
    ref_materia_prima: str | None = None
    descricao_materia_prima: str | None = None
    unidade: str | None = None
    quantidade: Decimal = Decimal("1")
    comp: Decimal | None = None
    larg: Decimal | None = None
    esp: Decimal | None = None
    area_m2: Decimal | None = None
    perimetro_ml: Decimal | None = None
    ml_orla_fina: Decimal | None = None
    ml_orla_grossa: Decimal | None = None
    custo_unitario: Decimal | None = None
    custo_total: Decimal | None = None
    margem_percentagem: Decimal | None = None
    preco_unitario: Decimal | None = None
    preco_total: Decimal | None = None
    def_operacao_id: int | None = None
    def_maquina_id: int | None = None
    tempo_calculado: Decimal | None = None
    tempo_manual: Decimal | None = None
    override_manual: bool = False
    editado_localmente: bool = False
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class AdicionarPecasResult:
    """Summary of adding library pieces as cost lines."""

    criadas: int
    componentes: int
    ignoradas: int
    avisos: list[str]


class OrcamentoItemCusteioLinhaService:
    """Application service for OrcamentoItemCusteioLinha workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoItemCusteioLinhaRepository(session)
        self.peca_repository = DefPecaRepository(session)
        self.componente_repository = DefPecaComponenteRepository(session)
        self.item_valueset_repository = OrcamentoItemValuesetLinhaRepository(session)

    def listar_linhas_do_item(
        self, orcamento_item_id: int
    ) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List cost lines of one budget item."""
        return self.repository.list_by_orcamento_item(orcamento_item_id)

    def listar_linhas_ativas_do_item(
        self, orcamento_item_id: int
    ) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List active cost lines of one budget item."""
        return self.repository.list_active_by_orcamento_item(orcamento_item_id)

    def listar_linhas_da_versao(
        self, orcamento_versao_id: int
    ) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List cost lines of all items in one budget version."""
        return self.repository.list_by_orcamento_versao(orcamento_versao_id)

    def obter_por_id(self, id: int) -> OrcamentoItemCusteioLinhaResumo | None:
        """Get one cost line by id."""
        return self.repository.get_by_id(id)

    def adicionar_pecas_da_biblioteca(
        self, orcamento_item_id: int, def_peca_ids: list[int]
    ) -> AdicionarPecasResult:
        """Create cost lines for selected library pieces.

        Simple pieces create one PECA line. Composite pieces create a main
        PECA_COMPOSTA line plus one sub-line per active component. Material data
        is resolved from the item ValueSet (default option of each key).
        """
        item_id = self._validate_required_id(orcamento_item_id, "orcamento_item_id")

        criadas = 0
        componentes = 0
        ignoradas = 0
        avisos: list[str] = []

        for def_peca_id in def_peca_ids:
            peca = self.peca_repository.get_by_id(def_peca_id)
            if peca is None:
                ignoradas += 1
                continue

            if peca.tipo_peca == COMPOSTA:
                componentes += self._adicionar_peca_composta(item_id, peca, avisos)
            else:
                self._adicionar_peca_simples(item_id, peca, avisos)
            criadas += 1

        self.session.commit()

        return AdicionarPecasResult(
            criadas=criadas,
            componentes=componentes,
            ignoradas=ignoradas,
            avisos=avisos,
        )

    def _adicionar_peca_simples(
        self, orcamento_item_id: int, peca: DefPecaResumo, avisos: list[str]
    ) -> None:
        """Create one PECA cost line for a simple library piece."""
        fields, aviso = self._build_peca_line_fields(
            orcamento_item_id,
            peca,
            tipo_linha=PECA,
            origem="BIBLIOTECA_PECA",
            nivel=0,
            linha_pai_id=None,
            ordem=None,
            qt_und=Decimal("1"),
        )
        if aviso:
            self._adicionar_aviso(avisos, aviso)

        self.repository.create_linha(**fields)

    def _adicionar_peca_composta(
        self, orcamento_item_id: int, peca: DefPecaResumo, avisos: list[str]
    ) -> int:
        """Create the main line plus component sub-lines of a composite piece.

        Returns the number of component sub-lines created.
        """
        principal = self._criar_linha_principal_composta(orcamento_item_id, peca)

        componentes = [
            componente
            for componente in self.componente_repository.list_by_peca_pai_id(peca.id)
            if componente.ativo
        ]
        if not componentes:
            self._adicionar_aviso(
                avisos, f"Peça composta {peca.codigo} sem componentes configurados."
            )
            return 0

        return self._criar_linhas_componentes(
            orcamento_item_id, componentes, principal.id, avisos
        )

    def _criar_linha_principal_composta(
        self, orcamento_item_id: int, peca: DefPecaResumo
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Create the main (grouping) line of a composite piece."""
        return self.repository.create_linha(
            orcamento_item_id=orcamento_item_id,
            tipo_linha=PECA_COMPOSTA,
            codigo=peca.codigo,
            def_peca_id=peca.id,
            def_peca_codigo=peca.codigo,
            descricao=peca.nome or peca.descricao or peca.codigo,
            codigo_orlas=self._format_codigo_orlas(peca),
            chave_valueset=peca.chave_valueset_material,
            origem_tipo="BIBLIOTECA_PECA",
            nivel=0,
            linha_pai_id=None,
            ordem=None,
            qt_mod=Decimal("1"),
            qt_und=Decimal("1"),
            quantidade=Decimal("1"),
            editado_localmente=False,
            ativo=True,
        )

    def _criar_linhas_componentes(
        self,
        orcamento_item_id: int,
        componentes: list,
        linha_pai_id: int,
        avisos: list[str],
    ) -> int:
        """Create one sub-line per component, returning how many were created."""
        criadas = 0
        for ordem, componente in enumerate(componentes, start=1):
            fields, aviso = self._build_componente_line_fields(
                orcamento_item_id, componente, linha_pai_id, ordem
            )
            if aviso:
                self._adicionar_aviso(avisos, aviso)
            self.repository.create_linha(**fields)
            criadas += 1

        return criadas

    def _build_componente_line_fields(
        self, orcamento_item_id: int, componente, linha_pai_id: int, ordem: int
    ) -> tuple[dict, str | None]:
        """Build the cost line fields for one composite component sub-line."""
        qt_und = (
            componente.quantidade if componente.quantidade is not None else Decimal("1")
        )
        tipo_linha = normalize_custeio_linha_type(componente.tipo_componente)

        peca_filha = self._obter_def_peca_filha(componente)

        if peca_filha is not None:
            return self._build_peca_line_fields(
                orcamento_item_id,
                peca_filha,
                tipo_linha=tipo_linha,
                origem="PECA_COMPOSTA",
                nivel=1,
                linha_pai_id=linha_pai_id,
                ordem=ordem,
                qt_und=qt_und,
                sem_chave_observacao="Componente sem chave ValueSet.",
            )

        fields: dict = {
            "orcamento_item_id": orcamento_item_id,
            "tipo_linha": tipo_linha,
            "codigo": componente.referencia_componente,
            "descricao": componente.descricao
            or componente.referencia_componente
            or "Componente",
            "origem_tipo": "PECA_COMPOSTA",
            "nivel": 1,
            "linha_pai_id": linha_pai_id,
            "ordem": ordem,
            "qt_mod": Decimal("1"),
            "qt_und": qt_und,
            "quantidade": qt_und,
            "editado_localmente": False,
            "ativo": True,
            "observacoes": "Componente sem definição de peça associada.",
        }
        return fields, None

    def _obter_def_peca_filha(self, componente) -> DefPecaResumo | None:
        """Resolve the child piece definition of a component.

        Prefers the explicit def_peca_componente_id link; falls back to looking
        the definition up by code (referencia_componente).
        """
        if componente.def_peca_componente_id is not None:
            peca = self.peca_repository.get_by_id(componente.def_peca_componente_id)
            if peca is not None:
                return peca

        if componente.referencia_componente:
            return self.peca_repository.get_by_codigo(componente.referencia_componente)

        return None

    def resolver_valueset_para_def_peca(
        self, orcamento_item_id: int, peca: DefPecaResumo
    ) -> OrcamentoItemValuesetLinhaResumo | None:
        """Resolve the item ValueSet line for a piece key (default option first)."""
        if not peca.chave_valueset_material:
            return None

        chave = normalize_valueset_key(peca.chave_valueset_material)

        padrao = self.item_valueset_repository.get_default_by_item_chave(
            orcamento_item_id, chave
        )
        if padrao is not None:
            return padrao

        for linha in self.item_valueset_repository.list_by_item_chave(
            orcamento_item_id, chave
        ):
            if linha.ativo:
                return linha

        return None

    def _build_peca_line_fields(
        self,
        orcamento_item_id: int,
        peca: DefPecaResumo,
        *,
        tipo_linha: str = PECA,
        origem: str = "BIBLIOTECA_PECA",
        nivel: int = 0,
        linha_pai_id: int | None = None,
        ordem: int | None = None,
        qt_und: Decimal = Decimal("1"),
        sem_chave_observacao: str = "Definição de peça sem chave ValueSet.",
    ) -> tuple[dict, str | None]:
        """Build the cost line fields for one piece, resolving the item ValueSet."""
        qt_und = qt_und if qt_und is not None else Decimal("1")

        fields: dict = {
            "orcamento_item_id": orcamento_item_id,
            "tipo_linha": tipo_linha,
            "codigo": peca.codigo,
            "def_peca_id": peca.id,
            "def_peca_codigo": peca.codigo,
            "descricao": peca.nome or peca.descricao or peca.codigo,
            "codigo_orlas": self._format_codigo_orlas(peca),
            "chave_valueset": peca.chave_valueset_material,
            "origem_tipo": origem,
            "nivel": nivel,
            "linha_pai_id": linha_pai_id,
            "ordem": ordem,
            "qt_mod": Decimal("1"),
            "qt_und": qt_und,
            "quantidade": qt_und,
            "editado_localmente": False,
            "ativo": True,
        }

        if not peca.chave_valueset_material:
            fields["observacoes"] = sem_chave_observacao
            return fields, None

        linha_vs = self.resolver_valueset_para_def_peca(orcamento_item_id, peca)
        if linha_vs is None:
            aviso = f"Sem ValueSet encontrado para a chave {peca.chave_valueset_material}"
            fields["observacoes"] = aviso
            return fields, aviso

        fields.update(
            {
                "materia_prima_id": linha_vs.materia_prima_id,
                "ref_materia_prima": linha_vs.ref_materia_prima,
                "descricao_materia_prima": linha_vs.descricao_materia_prima,
                "mat_default": linha_vs.codigo_opcao or linha_vs.nome_opcao,
                "ref_le": linha_vs.ref_le,
                "descricao_no_orcamento": linha_vs.descricao_no_orcamento,
                "unidade": linha_vs.unidade,
                "preco_liquido": linha_vs.preco_liquido,
                "desperdicio_percentagem": linha_vs.desperdicio_percentagem,
                "tipo_materia_prima": linha_vs.tipo_materia_prima,
                "familia_materia_prima": linha_vs.familia_materia_prima,
                "coresp_orla_0_4": linha_vs.coresp_orla_0_4,
                "coresp_orla_1_0": linha_vs.coresp_orla_1_0,
                "comp_mp": linha_vs.comp_mp,
                "larg_mp": linha_vs.larg_mp,
                "esp_mp": linha_vs.esp_mp,
            }
        )
        return fields, None

    def _format_codigo_orlas(self, peca: DefPecaResumo) -> str:
        """Build the orla code (e.g. 2200) from the four orla sides."""
        return f"{peca.orla_c1}{peca.orla_c2}{peca.orla_l1}{peca.orla_l2}"

    def _adicionar_aviso(self, avisos: list[str], mensagem: str) -> None:
        """Append a warning message, avoiding duplicates."""
        if mensagem not in avisos:
            avisos.append(mensagem)

    def criar_linha_manual(
        self, data: CriarLinhaCusteioData
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Create one cost line (manual or with a given type)."""
        fields = self._build_fields(data)
        result = self.repository.create_linha(**fields)
        self.session.commit()

        return result

    def editar_linha(
        self, id: int, data: EditarLinhaCusteioData
    ) -> OrcamentoItemCusteioLinhaResumo:
        """Edit one cost line."""
        fields = self._build_fields(data)
        result = self.repository.update_linha(id=id, **fields)
        self.session.commit()

        return result

    def desativar_linha(self, id: int) -> bool:
        """Deactivate one cost line."""
        deactivated = self.repository.deactivate_linha(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_linha(self, id: int) -> bool:
        """Reactivate one cost line."""
        activated = self.repository.activate_linha(id)
        if activated:
            self.session.commit()

        return activated

    def _build_fields(self, data) -> dict:
        orcamento_item_id = self._validate_required_id(
            data.orcamento_item_id, "orcamento_item_id"
        )
        descricao = self._normalize_required_text(data.descricao, "descricao")
        tipo_linha = self._normalize_tipo_linha(data.tipo_linha)
        quantidade = self._normalize_quantidade(data.quantidade)
        custo_total = self._compute_total(data.custo_total, data.custo_unitario, quantidade)
        preco_total = self._compute_total(data.preco_total, data.preco_unitario, quantidade)

        return {
            "orcamento_item_id": orcamento_item_id,
            "orcamento_item_modulo_id": data.orcamento_item_modulo_id,
            "origem_tipo": data.origem_tipo,
            "origem_id": data.origem_id,
            "tipo_linha": tipo_linha,
            "codigo": data.codigo,
            "descricao": descricao,
            "materia_prima_id": data.materia_prima_id,
            "ref_materia_prima": data.ref_materia_prima,
            "descricao_materia_prima": data.descricao_materia_prima,
            "unidade": data.unidade,
            "quantidade": quantidade,
            "comp": data.comp,
            "larg": data.larg,
            "esp": data.esp,
            "area_m2": data.area_m2,
            "perimetro_ml": data.perimetro_ml,
            "ml_orla_fina": data.ml_orla_fina,
            "ml_orla_grossa": data.ml_orla_grossa,
            "custo_unitario": data.custo_unitario,
            "custo_total": custo_total,
            "margem_percentagem": data.margem_percentagem,
            "preco_unitario": data.preco_unitario,
            "preco_total": preco_total,
            "def_operacao_id": data.def_operacao_id,
            "def_maquina_id": data.def_maquina_id,
            "tempo_calculado": data.tempo_calculado,
            "tempo_manual": data.tempo_manual,
            "override_manual": data.override_manual,
            "editado_localmente": data.editado_localmente,
            "ativo": data.ativo,
            "observacoes": data.observacoes,
        }

    def _validate_required_id(self, value: int | None, field_name: str) -> int:
        if not value:
            raise ValueError(f"{field_name} is required")

        return value

    def _normalize_required_text(self, value: str | None, field_name: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} is required")

        return normalized

    def _normalize_tipo_linha(self, tipo_linha: str | None) -> str:
        if tipo_linha is None or not tipo_linha.strip():
            return MANUAL

        return normalize_custeio_linha_type(tipo_linha)

    def _normalize_quantidade(self, quantidade: Decimal | None) -> Decimal:
        if quantidade is None:
            return Decimal("1")

        return quantidade

    def _compute_total(
        self,
        total: Decimal | None,
        unitario: Decimal | None,
        quantidade: Decimal,
    ) -> Decimal | None:
        if total is not None:
            return total

        if unitario is not None:
            return unitario * quantidade

        return None
