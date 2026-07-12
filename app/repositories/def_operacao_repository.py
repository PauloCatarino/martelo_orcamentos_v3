"""Repository for operation catalog reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefOperacao


@dataclass(frozen=True)
class DefOperacaoResumo:
    """Read model for reusable operation definitions."""

    id: int
    codigo: str
    nome: str
    descricao: str | None
    tipo_operacao: str | None
    unidade_calculo: str | None
    tempo_base: Decimal | None
    tempo_setup: Decimal | None
    custo_hora: Decimal | None
    custo_minimo: Decimal | None
    maquina_id: int | None
    ativo: bool
    observacoes: str | None
    maquina_codigo: str | None = None
    maquina_permite_rasgos: bool = False
    maquina_preco_rasgo_ml_std: Decimal | None = None
    # Real machine tariffs (STD), so the dialogs can simulate with the same
    # numbers the costing uses (phase G2).
    maquina_custo_hora_std: Decimal | None = None
    maquina_custo_hora_serie: Decimal | None = None
    maquina_preco_ml_std: Decimal | None = None
    maquina_preco_lado_curto_std: Decimal | None = None
    maquina_preco_lado_longo_std: Decimal | None = None
    maquina_limite_lado_mm: Decimal | None = None
    maquina_custo_setup_peca_std: Decimal | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefOperacaoRepository:
    """Repository for DefOperacao operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefOperacaoResumo]:
        """List all operations."""
        statement = select(DefOperacao).order_by(
            DefOperacao.nome.asc(),
            DefOperacao.codigo.asc(),
        )
        operacoes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(operacao) for operacao in operacoes]

    def list_active(self) -> list[DefOperacaoResumo]:
        """List active operations."""
        statement = (
            select(DefOperacao)
            .where(DefOperacao.ativo.is_(True))
            .order_by(DefOperacao.nome.asc(), DefOperacao.codigo.asc())
        )
        operacoes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(operacao) for operacao in operacoes]

    def get_by_id(self, id: int) -> DefOperacaoResumo | None:
        """Get one operation by id."""
        operacao = self.session.get(DefOperacao, id)
        if operacao is None:
            return None

        return self._to_resumo(operacao)

    def get_by_codigo(self, codigo: str) -> DefOperacaoResumo | None:
        """Get one operation by code."""
        statement = select(DefOperacao).where(DefOperacao.codigo == codigo)
        operacao = self.session.execute(statement).scalars().first()
        if operacao is None:
            return None

        return self._to_resumo(operacao)

    def create_operacao(
        self,
        *,
        codigo: str,
        nome: str,
        descricao: str | None = None,
        tipo_operacao: str | None = None,
        unidade_calculo: str | None = None,
        tempo_base: Decimal | None = None,
        tempo_setup: Decimal | None = None,
        custo_hora: Decimal | None = None,
        custo_minimo: Decimal | None = None,
        maquina_id: int | None = None,
        ativo: bool = True,
        observacoes: str | None = None,
    ) -> DefOperacaoResumo:
        """Create one operation."""
        operacao = DefOperacao(
            codigo=codigo,
            nome=nome,
            descricao=descricao,
            tipo_operacao=tipo_operacao,
            unidade_calculo=unidade_calculo,
            tempo_base=tempo_base,
            tempo_setup=tempo_setup,
            custo_hora=custo_hora,
            custo_minimo=custo_minimo,
            maquina_id=maquina_id,
            ativo=ativo,
            observacoes=observacoes,
        )
        self.session.add(operacao)
        self.session.flush()

        return self._to_resumo(operacao)

    def update_operacao(
        self,
        *,
        id: int,
        codigo: str,
        nome: str,
        descricao: str | None = None,
        tipo_operacao: str | None = None,
        unidade_calculo: str | None = None,
        tempo_base: Decimal | None = None,
        tempo_setup: Decimal | None = None,
        custo_hora: Decimal | None = None,
        custo_minimo: Decimal | None = None,
        maquina_id: int | None = None,
        ativo: bool = True,
        observacoes: str | None = None,
    ) -> DefOperacaoResumo:
        """Update one operation."""
        operacao = self.session.get(DefOperacao, id)
        if operacao is None:
            raise ValueError("def_operacao not found")

        operacao.codigo = codigo
        operacao.nome = nome
        operacao.descricao = descricao
        operacao.tipo_operacao = tipo_operacao
        operacao.unidade_calculo = unidade_calculo
        operacao.tempo_base = tempo_base
        operacao.tempo_setup = tempo_setup
        operacao.custo_hora = custo_hora
        operacao.custo_minimo = custo_minimo
        operacao.maquina_id = maquina_id
        operacao.ativo = ativo
        operacao.observacoes = observacoes
        self.session.flush()

        return self._to_resumo(operacao)

    def deactivate_operacao(self, id: int) -> bool:
        """Deactivate one operation."""
        operacao = self.session.get(DefOperacao, id)
        if operacao is None:
            return False

        operacao.ativo = False
        self.session.flush()

        return True

    def activate_operacao(self, id: int) -> bool:
        """Reactivate one operation."""
        operacao = self.session.get(DefOperacao, id)
        if operacao is None:
            return False

        operacao.ativo = True
        self.session.flush()

        return True

    def _to_resumo(self, operacao: DefOperacao) -> DefOperacaoResumo:
        """Convert an ORM operation to the read model."""
        return DefOperacaoResumo(
            id=operacao.id,
            codigo=operacao.codigo,
            nome=operacao.nome,
            descricao=operacao.descricao,
            tipo_operacao=operacao.tipo_operacao,
            unidade_calculo=operacao.unidade_calculo,
            tempo_base=operacao.tempo_base,
            tempo_setup=operacao.tempo_setup,
            custo_hora=operacao.custo_hora,
            custo_minimo=operacao.custo_minimo,
            maquina_id=operacao.maquina_id,
            ativo=operacao.ativo,
            observacoes=operacao.observacoes,
            maquina_codigo=getattr(operacao.maquina, "codigo", None),
            maquina_permite_rasgos=bool(getattr(operacao.maquina, "permite_rasgos", False)),
            maquina_preco_rasgo_ml_std=getattr(operacao.maquina, "preco_rasgo_ml_std", None),
            maquina_custo_hora_std=getattr(operacao.maquina, "custo_hora", None),
            maquina_custo_hora_serie=getattr(operacao.maquina, "custo_hora_serie", None),
            maquina_preco_ml_std=getattr(operacao.maquina, "preco_ml_std", None),
            maquina_preco_lado_curto_std=getattr(
                operacao.maquina, "preco_lado_curto_std", None
            ),
            maquina_preco_lado_longo_std=getattr(
                operacao.maquina, "preco_lado_longo_std", None
            ),
            maquina_limite_lado_mm=getattr(operacao.maquina, "limite_lado_mm", None),
            maquina_custo_setup_peca_std=getattr(
                operacao.maquina, "custo_setup_peca_std", None
            ),
            created_at=operacao.created_at,
            updated_at=operacao.updated_at,
        )
