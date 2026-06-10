"""Repository for machine catalog reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefMaquina


@dataclass(frozen=True)
class DefMaquinaResumo:
    """Read model for reusable machine definitions."""

    id: int
    codigo: str
    nome: str
    descricao: str | None
    tipo: str | None
    custo_hora: Decimal | None
    ativo: bool
    observacoes: str | None
    custo_hora_serie: Decimal | None = None
    preco_ml_std: Decimal | None = None
    preco_ml_serie: Decimal | None = None
    custo_setup_peca_std: Decimal | None = None
    custo_setup_peca_serie: Decimal | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefMaquinaRepository:
    """Repository for DefMaquina operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefMaquinaResumo]:
        """List all machines."""
        statement = select(DefMaquina).order_by(DefMaquina.nome.asc(), DefMaquina.codigo.asc())
        maquinas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(maquina) for maquina in maquinas]

    def list_active(self) -> list[DefMaquinaResumo]:
        """List active machines."""
        statement = (
            select(DefMaquina)
            .where(DefMaquina.ativo.is_(True))
            .order_by(DefMaquina.nome.asc(), DefMaquina.codigo.asc())
        )
        maquinas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(maquina) for maquina in maquinas]

    def get_by_id(self, id: int) -> DefMaquinaResumo | None:
        """Get one machine by id."""
        maquina = self.session.get(DefMaquina, id)
        if maquina is None:
            return None

        return self._to_resumo(maquina)

    def get_by_codigo(self, codigo: str) -> DefMaquinaResumo | None:
        """Get one machine by code."""
        statement = select(DefMaquina).where(DefMaquina.codigo == codigo)
        maquina = self.session.execute(statement).scalars().first()
        if maquina is None:
            return None

        return self._to_resumo(maquina)

    def create_maquina(
        self,
        *,
        codigo: str,
        nome: str,
        descricao: str | None = None,
        tipo: str | None = None,
        custo_hora: Decimal | None = None,
        custo_hora_serie: Decimal | None = None,
        preco_ml_std: Decimal | None = None,
        preco_ml_serie: Decimal | None = None,
        custo_setup_peca_std: Decimal | None = None,
        custo_setup_peca_serie: Decimal | None = None,
        ativo: bool = True,
        observacoes: str | None = None,
    ) -> DefMaquinaResumo:
        """Create one machine."""
        maquina = DefMaquina(
            codigo=codigo,
            nome=nome,
            descricao=descricao,
            tipo=tipo,
            custo_hora=custo_hora,
            custo_hora_serie=custo_hora_serie,
            preco_ml_std=preco_ml_std,
            preco_ml_serie=preco_ml_serie,
            custo_setup_peca_std=custo_setup_peca_std,
            custo_setup_peca_serie=custo_setup_peca_serie,
            ativo=ativo,
            observacoes=observacoes,
        )
        self.session.add(maquina)
        self.session.flush()

        return self._to_resumo(maquina)

    def update_maquina(
        self,
        *,
        id: int,
        codigo: str,
        nome: str,
        descricao: str | None = None,
        tipo: str | None = None,
        custo_hora: Decimal | None = None,
        custo_hora_serie: Decimal | None = None,
        preco_ml_std: Decimal | None = None,
        preco_ml_serie: Decimal | None = None,
        custo_setup_peca_std: Decimal | None = None,
        custo_setup_peca_serie: Decimal | None = None,
        ativo: bool = True,
        observacoes: str | None = None,
    ) -> DefMaquinaResumo:
        """Update one machine."""
        maquina = self.session.get(DefMaquina, id)
        if maquina is None:
            raise ValueError("def_maquina not found")

        maquina.codigo = codigo
        maquina.nome = nome
        maquina.descricao = descricao
        maquina.tipo = tipo
        maquina.custo_hora = custo_hora
        maquina.custo_hora_serie = custo_hora_serie
        maquina.preco_ml_std = preco_ml_std
        maquina.preco_ml_serie = preco_ml_serie
        maquina.custo_setup_peca_std = custo_setup_peca_std
        maquina.custo_setup_peca_serie = custo_setup_peca_serie
        maquina.ativo = ativo
        maquina.observacoes = observacoes
        self.session.flush()

        return self._to_resumo(maquina)

    def deactivate_maquina(self, id: int) -> bool:
        """Deactivate one machine."""
        maquina = self.session.get(DefMaquina, id)
        if maquina is None:
            return False

        maquina.ativo = False
        self.session.flush()

        return True

    def activate_maquina(self, id: int) -> bool:
        """Reactivate one machine."""
        maquina = self.session.get(DefMaquina, id)
        if maquina is None:
            return False

        maquina.ativo = True
        self.session.flush()

        return True

    def _to_resumo(self, maquina: DefMaquina) -> DefMaquinaResumo:
        """Convert an ORM machine to the read model."""
        return DefMaquinaResumo(
            id=maquina.id,
            codigo=maquina.codigo,
            nome=maquina.nome,
            descricao=maquina.descricao,
            tipo=maquina.tipo,
            custo_hora=maquina.custo_hora,
            custo_hora_serie=maquina.custo_hora_serie,
            preco_ml_std=maquina.preco_ml_std,
            preco_ml_serie=maquina.preco_ml_serie,
            custo_setup_peca_std=maquina.custo_setup_peca_std,
            custo_setup_peca_serie=maquina.custo_setup_peca_serie,
            ativo=maquina.ativo,
            observacoes=maquina.observacoes,
            created_at=maquina.created_at,
            updated_at=maquina.updated_at,
        )
