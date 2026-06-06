"""Repository for budget item cost line reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OrcamentoItemCusteioLinha


@dataclass(frozen=True)
class OrcamentoItemCusteioLinhaResumo:
    """Read model for budget item cost lines."""

    id: int
    orcamento_item_id: int
    orcamento_item_modulo_id: int | None
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
    comp: Decimal | None
    larg: Decimal | None
    esp: Decimal | None
    area_m2: Decimal | None
    perimetro_ml: Decimal | None
    ml_orla_fina: Decimal | None
    ml_orla_grossa: Decimal | None
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
            created_at=linha.created_at,
            updated_at=linha.updated_at,
        )
