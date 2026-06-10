"""Repository for budget item cost line reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models import OrcamentoItem, OrcamentoItemCusteioLinha


@dataclass(frozen=True)
class OrcamentoItemCusteioLinhaResumo:
    """Read model for budget item cost lines."""

    id: int
    orcamento_item_id: int
    orcamento_item_modulo_id: int | None
    linha_pai_id: int | None
    nivel: int
    ordem: int | None
    origem_tipo: str | None
    origem_id: int | None
    tipo_linha: str
    codigo: str | None
    descricao: str
    materia_prima_id: int | None
    ref_materia_prima: str | None
    descricao_materia_prima: str | None
    unidade: str | None
    quantidade: Decimal
    comp: str | None
    larg: str | None
    esp: str | None
    area_m2: Decimal | None
    perimetro_ml: Decimal | None
    ml_orla_fina: Decimal | None
    ml_orla_grossa: Decimal | None
    custo_orla_fina: Decimal | None
    custo_orla_grossa: Decimal | None
    custo_orlas: Decimal | None
    custo_mp: Decimal | None
    custo_ferragem: Decimal | None
    custo_acabamento: Decimal | None
    custo_corte: Decimal | None
    custo_orlagem: Decimal | None
    custo_producao: Decimal | None
    consumo_ml_unitario: Decimal | None
    consumo_ml_total: Decimal | None
    custo_unitario: Decimal | None
    custo_total: Decimal | None
    margem_percentagem: Decimal | None
    preco_unitario: Decimal | None
    preco_total: Decimal | None
    def_operacao_id: int | None
    def_maquina_id: int | None
    tempo_calculado: Decimal | None
    tempo_manual: Decimal | None
    override_manual: bool
    editado_localmente: bool
    ativo: bool
    observacoes: str | None
    def_peca_id: int | None = None
    def_peca_codigo: str | None = None
    chave_valueset: str | None = None
    codigo_orlas: str | None = None
    mat_default: str | None = None
    ref_le: str | None = None
    descricao_no_orcamento: str | None = None
    preco_liquido: Decimal | None = None
    desperdicio_percentagem: Decimal | None = None
    tipo_materia_prima: str | None = None
    familia_materia_prima: str | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    comp_mp: Decimal | None = None
    larg_mp: Decimal | None = None
    esp_mp: Decimal | None = None
    qt_mod: Decimal | None = None
    qt_und: Decimal | None = None
    comp_real: Decimal | None = None
    larg_real: Decimal | None = None
    esp_real: Decimal | None = None
    material_editado_localmente: bool = False
    origem_material: str | None = None
    excluir_mp: bool = False
    excluir_orla: bool = False
    excluir_ferragem: bool = False
    excluir_producao: bool = False
    excluir_acabamento: bool = False
    excluir_mo: bool = False
    acabamento_face_sup: str | None = None
    acabamento_face_inf: str | None = None
    area_acabamento_sup: Decimal | None = None
    area_acabamento_inf: Decimal | None = None
    acabamento_editado_localmente: bool = False
    acabamento_sup_ref_le: str | None = None
    acabamento_sup_descricao: str | None = None
    acabamento_sup_unidade: str | None = None
    acabamento_sup_preco_liquido: Decimal | None = None
    acabamento_sup_desperdicio_percentagem: Decimal | None = None
    acabamento_inf_ref_le: str | None = None
    acabamento_inf_descricao: str | None = None
    acabamento_inf_unidade: str | None = None
    acabamento_inf_preco_liquido: Decimal | None = None
    acabamento_inf_desperdicio_percentagem: Decimal | None = None
    operacoes: str | None = None
    maquina: str | None = None
    tipo_producao: str | None = None
    tempo_corte: Decimal | None = None
    tempo_orlagem: Decimal | None = None
    tempo_cnc: Decimal | None = None
    tempo_montagem: Decimal | None = None
    tempo_setup: Decimal | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrcamentoItemCusteioLinhaRepository:
    """Repository for OrcamentoItemCusteioLinha operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_orcamento_item(self, orcamento_item_id: int) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List cost lines of one budget item."""
        statement = (
            select(OrcamentoItemCusteioLinha)
            .where(OrcamentoItemCusteioLinha.orcamento_item_id == orcamento_item_id)
            .order_by(OrcamentoItemCusteioLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_active_by_orcamento_item(
        self, orcamento_item_id: int
    ) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List active cost lines of one budget item."""
        statement = (
            select(OrcamentoItemCusteioLinha)
            .where(
                OrcamentoItemCusteioLinha.orcamento_item_id == orcamento_item_id,
                OrcamentoItemCusteioLinha.ativo.is_(True),
            )
            .order_by(OrcamentoItemCusteioLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def list_by_orcamento_versao(
        self, orcamento_versao_id: int
    ) -> list[OrcamentoItemCusteioLinhaResumo]:
        """List cost lines of all items in one budget version."""
        statement = (
            select(OrcamentoItemCusteioLinha)
            .join(
                OrcamentoItem,
                OrcamentoItemCusteioLinha.orcamento_item_id == OrcamentoItem.id,
            )
            .where(OrcamentoItem.orcamento_versao_id == orcamento_versao_id)
            .order_by(OrcamentoItem.ordem.asc(), OrcamentoItemCusteioLinha.id.asc())
        )
        linhas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(linha) for linha in linhas]

    def get_by_id(self, id: int) -> OrcamentoItemCusteioLinhaResumo | None:
        """Get one cost line by id."""
        linha = self.session.get(OrcamentoItemCusteioLinha, id)
        if linha is None:
            return None

        return self._to_resumo(linha)

    def create_linha(self, **fields) -> OrcamentoItemCusteioLinhaResumo:
        """Create one cost line."""
        linha = OrcamentoItemCusteioLinha(**fields)
        self.session.add(linha)
        self.session.flush()

        return self._to_resumo(linha)

    def update_linha(self, *, id: int, **fields) -> OrcamentoItemCusteioLinhaResumo:
        """Update one cost line."""
        linha = self.session.get(OrcamentoItemCusteioLinha, id)
        if linha is None:
            raise ValueError("orcamento_item_custeio_linha not found")

        for name, value in fields.items():
            setattr(linha, name, value)
        self.session.flush()

        return self._to_resumo(linha)

    def deactivate_linha(self, id: int) -> bool:
        """Deactivate one cost line."""
        linha = self.session.get(OrcamentoItemCusteioLinha, id)
        if linha is None:
            return False

        linha.ativo = False
        self.session.flush()

        return True

    def atualizar_flag_exclusao(
        self, orcamento_item_id: int, campo: str, valor: bool
    ) -> int:
        """Set one exclusion flag on all active lines of the item; returns count.

        ``campo`` must be validated by the caller (it is interpolated into the
        update). Inactive lines are not touched.
        """
        result = self.session.execute(
            update(OrcamentoItemCusteioLinha)
            .where(
                OrcamentoItemCusteioLinha.orcamento_item_id == orcamento_item_id,
                OrcamentoItemCusteioLinha.ativo.is_(True),
            )
            .values(**{campo: bool(valor)})
        )
        self.session.flush()

        return result.rowcount or 0

    def delete_linhas(self, ids: list[int]) -> int:
        """Physically delete the given cost lines; returns how many were removed.

        Any remaining line whose parent (linha_pai_id) is being deleted is
        orphaned (linha_pai_id set to None) first, to avoid self-FK violations
        without deleting child lines automatically.
        """
        valid_ids = [id for id in ids if id is not None]
        if not valid_ids:
            return 0

        self.session.execute(
            update(OrcamentoItemCusteioLinha)
            .where(OrcamentoItemCusteioLinha.linha_pai_id.in_(valid_ids))
            .values(linha_pai_id=None)
        )
        result = self.session.execute(
            delete(OrcamentoItemCusteioLinha).where(
                OrcamentoItemCusteioLinha.id.in_(valid_ids)
            )
        )
        self.session.flush()

        return result.rowcount or 0

    def activate_linha(self, id: int) -> bool:
        """Reactivate one cost line."""
        linha = self.session.get(OrcamentoItemCusteioLinha, id)
        if linha is None:
            return False

        linha.ativo = True
        self.session.flush()

        return True

    def _to_resumo(self, linha: OrcamentoItemCusteioLinha) -> OrcamentoItemCusteioLinhaResumo:
        """Convert an ORM cost line to the read model."""
        return OrcamentoItemCusteioLinhaResumo(
            id=linha.id,
            orcamento_item_id=linha.orcamento_item_id,
            orcamento_item_modulo_id=linha.orcamento_item_modulo_id,
            linha_pai_id=linha.linha_pai_id,
            nivel=linha.nivel,
            ordem=linha.ordem,
            origem_tipo=linha.origem_tipo,
            origem_id=linha.origem_id,
            tipo_linha=linha.tipo_linha,
            codigo=linha.codigo,
            descricao=linha.descricao,
            materia_prima_id=linha.materia_prima_id,
            ref_materia_prima=linha.ref_materia_prima,
            descricao_materia_prima=linha.descricao_materia_prima,
            unidade=linha.unidade,
            quantidade=linha.quantidade,
            comp=linha.comp,
            larg=linha.larg,
            esp=linha.esp,
            area_m2=linha.area_m2,
            perimetro_ml=linha.perimetro_ml,
            ml_orla_fina=linha.ml_orla_fina,
            ml_orla_grossa=linha.ml_orla_grossa,
            custo_orla_fina=linha.custo_orla_fina,
            custo_orla_grossa=linha.custo_orla_grossa,
            custo_orlas=linha.custo_orlas,
            custo_mp=linha.custo_mp,
            custo_ferragem=linha.custo_ferragem,
            custo_acabamento=linha.custo_acabamento,
            custo_corte=linha.custo_corte,
            custo_orlagem=linha.custo_orlagem,
            custo_producao=linha.custo_producao,
            consumo_ml_unitario=linha.consumo_ml_unitario,
            consumo_ml_total=linha.consumo_ml_total,
            acabamento_face_sup=linha.acabamento_face_sup,
            acabamento_face_inf=linha.acabamento_face_inf,
            area_acabamento_sup=linha.area_acabamento_sup,
            area_acabamento_inf=linha.area_acabamento_inf,
            acabamento_editado_localmente=linha.acabamento_editado_localmente,
            acabamento_sup_ref_le=linha.acabamento_sup_ref_le,
            acabamento_sup_descricao=linha.acabamento_sup_descricao,
            acabamento_sup_unidade=linha.acabamento_sup_unidade,
            acabamento_sup_preco_liquido=linha.acabamento_sup_preco_liquido,
            acabamento_sup_desperdicio_percentagem=(
                linha.acabamento_sup_desperdicio_percentagem
            ),
            acabamento_inf_ref_le=linha.acabamento_inf_ref_le,
            acabamento_inf_descricao=linha.acabamento_inf_descricao,
            acabamento_inf_unidade=linha.acabamento_inf_unidade,
            acabamento_inf_preco_liquido=linha.acabamento_inf_preco_liquido,
            acabamento_inf_desperdicio_percentagem=(
                linha.acabamento_inf_desperdicio_percentagem
            ),
            operacoes=linha.operacoes,
            maquina=linha.maquina,
            tipo_producao=linha.tipo_producao,
            tempo_corte=linha.tempo_corte,
            tempo_orlagem=linha.tempo_orlagem,
            tempo_cnc=linha.tempo_cnc,
            tempo_montagem=linha.tempo_montagem,
            tempo_setup=linha.tempo_setup,
            excluir_mp=linha.excluir_mp,
            excluir_orla=linha.excluir_orla,
            excluir_ferragem=linha.excluir_ferragem,
            excluir_producao=linha.excluir_producao,
            excluir_acabamento=linha.excluir_acabamento,
            excluir_mo=linha.excluir_mo,
            custo_unitario=linha.custo_unitario,
            custo_total=linha.custo_total,
            margem_percentagem=linha.margem_percentagem,
            preco_unitario=linha.preco_unitario,
            preco_total=linha.preco_total,
            def_operacao_id=linha.def_operacao_id,
            def_maquina_id=linha.def_maquina_id,
            tempo_calculado=linha.tempo_calculado,
            tempo_manual=linha.tempo_manual,
            override_manual=linha.override_manual,
            editado_localmente=linha.editado_localmente,
            ativo=linha.ativo,
            observacoes=linha.observacoes,
            def_peca_id=linha.def_peca_id,
            def_peca_codigo=linha.def_peca_codigo,
            chave_valueset=linha.chave_valueset,
            codigo_orlas=linha.codigo_orlas,
            mat_default=linha.mat_default,
            ref_le=linha.ref_le,
            descricao_no_orcamento=linha.descricao_no_orcamento,
            preco_liquido=linha.preco_liquido,
            desperdicio_percentagem=linha.desperdicio_percentagem,
            tipo_materia_prima=linha.tipo_materia_prima,
            familia_materia_prima=linha.familia_materia_prima,
            coresp_orla_0_4=linha.coresp_orla_0_4,
            coresp_orla_1_0=linha.coresp_orla_1_0,
            comp_mp=linha.comp_mp,
            larg_mp=linha.larg_mp,
            esp_mp=linha.esp_mp,
            qt_mod=linha.qt_mod,
            qt_und=linha.qt_und,
            comp_real=linha.comp_real,
            larg_real=linha.larg_real,
            esp_real=linha.esp_real,
            material_editado_localmente=linha.material_editado_localmente,
            origem_material=linha.origem_material,
            created_at=linha.created_at,
            updated_at=linha.updated_at,
        )
