"""Service for budget item cost line workflows.

This phase only stores cost lines. It does not generate lines automatically
from pieces, modules or operations, and does not recompute budget totals.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.custeio_linha_types import MANUAL, normalize_custeio_linha_type
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
    OrcamentoItemCusteioLinhaResumo,
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


class OrcamentoItemCusteioLinhaService:
    """Application service for OrcamentoItemCusteioLinha workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoItemCusteioLinhaRepository(session)

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

    def obter_por_id(self, id: int) -> OrcamentoItemCusteioLinhaResumo | None:
        """Get one cost line by id."""
        return self.repository.get_by_id(id)

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
