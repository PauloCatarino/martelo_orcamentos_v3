"""Repository for piece definition catalog reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefPeca


@dataclass(frozen=True)
class DefPecaResumo:
    """Read model for listing reusable piece definitions."""

    id: int
    codigo: str
    nome: str
    descricao: str | None
    grupo: str | None
    tipo_peca: str
    ativo: bool
    orla_c1: int = 0
    orla_c2: int = 0
    orla_l1: int = 0
    orla_l2: int = 0
    chave_valueset_material: str | None = None
    permite_acabamento: bool = False
    chave_valueset_acabamento_sup: str | None = None
    chave_valueset_acabamento_inf: str | None = None
    sem_material: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefPecaRepository:
    """Repository for DefPeca operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefPecaResumo]:
        """List all piece definitions."""
        statement = select(DefPeca).order_by(DefPeca.nome.asc(), DefPeca.codigo.asc())
        pecas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(peca) for peca in pecas]

    def list_ativas_para_biblioteca(self) -> list[DefPecaResumo]:
        """List active piece definitions for the costing library tree."""
        statement = (
            select(DefPeca)
            .where(DefPeca.ativo.is_(True))
            .order_by(DefPeca.grupo.asc(), DefPeca.nome.asc(), DefPeca.codigo.asc())
        )
        pecas = self.session.execute(statement).scalars().all()

        return [self._to_resumo(peca) for peca in pecas]

    def get_by_id(self, id: int) -> DefPecaResumo | None:
        """Get one piece definition by id."""
        peca = self.session.get(DefPeca, id)
        if peca is None:
            return None

        return self._to_resumo(peca)

    def get_by_codigo(self, codigo: str) -> DefPecaResumo | None:
        """Get one piece definition by code."""
        statement = select(DefPeca).where(DefPeca.codigo == codigo)
        peca = self.session.execute(statement).scalars().first()
        if peca is None:
            return None

        return self._to_resumo(peca)

    def create_def_peca(
        self,
        *,
        codigo: str,
        nome: str,
        descricao: str | None,
        grupo: str | None,
        tipo_peca: str,
        orla_c1: int = 0,
        orla_c2: int = 0,
        orla_l1: int = 0,
        orla_l2: int = 0,
        chave_valueset_material: str | None = None,
        permite_acabamento: bool = False,
        chave_valueset_acabamento_sup: str | None = None,
        chave_valueset_acabamento_inf: str | None = None,
        sem_material: bool = False,
        ativo: bool = True,
    ) -> DefPecaResumo:
        """Create one reusable piece definition."""
        peca = DefPeca(
            codigo=codigo,
            nome=nome,
            descricao=descricao,
            grupo=grupo,
            tipo_peca=tipo_peca,
            orla_c1=orla_c1,
            orla_c2=orla_c2,
            orla_l1=orla_l1,
            orla_l2=orla_l2,
            chave_valueset_material=chave_valueset_material,
            permite_acabamento=permite_acabamento,
            chave_valueset_acabamento_sup=chave_valueset_acabamento_sup,
            chave_valueset_acabamento_inf=chave_valueset_acabamento_inf,
            sem_material=sem_material,
            ativo=ativo,
        )
        self.session.add(peca)
        self.session.flush()

        return self._to_resumo(peca)

    def update_def_peca(
        self,
        *,
        id: int,
        codigo: str,
        nome: str,
        descricao: str | None,
        grupo: str | None,
        tipo_peca: str,
        orla_c1: int = 0,
        orla_c2: int = 0,
        orla_l1: int = 0,
        orla_l2: int = 0,
        chave_valueset_material: str | None = None,
        permite_acabamento: bool = False,
        chave_valueset_acabamento_sup: str | None = None,
        chave_valueset_acabamento_inf: str | None = None,
        sem_material: bool = False,
        ativo: bool,
    ) -> DefPecaResumo:
        """Update one reusable piece definition."""
        peca = self.session.get(DefPeca, id)
        if peca is None:
            raise ValueError("def_peca not found")

        peca.codigo = codigo
        peca.nome = nome
        peca.descricao = descricao
        peca.grupo = grupo
        peca.tipo_peca = tipo_peca
        peca.orla_c1 = orla_c1
        peca.orla_c2 = orla_c2
        peca.orla_l1 = orla_l1
        peca.orla_l2 = orla_l2
        peca.chave_valueset_material = chave_valueset_material
        peca.permite_acabamento = permite_acabamento
        peca.chave_valueset_acabamento_sup = chave_valueset_acabamento_sup
        peca.chave_valueset_acabamento_inf = chave_valueset_acabamento_inf
        peca.sem_material = sem_material
        peca.ativo = ativo
        self.session.flush()

        return self._to_resumo(peca)

    def deactivate_def_peca(self, id: int) -> bool:
        """Deactivate one reusable piece definition."""
        peca = self.session.get(DefPeca, id)
        if peca is None:
            return False

        peca.ativo = False
        self.session.flush()

        return True

    def activate_def_peca(self, id: int) -> bool:
        """Activate one reusable piece definition."""
        peca = self.session.get(DefPeca, id)
        if peca is None:
            return False

        peca.ativo = True
        self.session.flush()

        return True

    def _to_resumo(self, peca: DefPeca) -> DefPecaResumo:
        """Convert an ORM piece definition to the read model."""
        return DefPecaResumo(
            id=peca.id,
            codigo=peca.codigo,
            nome=peca.nome,
            descricao=peca.descricao,
            grupo=peca.grupo,
            tipo_peca=peca.tipo_peca,
            ativo=peca.ativo,
            orla_c1=peca.orla_c1,
            orla_c2=peca.orla_c2,
            orla_l1=peca.orla_l1,
            orla_l2=peca.orla_l2,
            chave_valueset_material=peca.chave_valueset_material,
            permite_acabamento=peca.permite_acabamento,
            chave_valueset_acabamento_sup=peca.chave_valueset_acabamento_sup,
            chave_valueset_acabamento_inf=peca.chave_valueset_acabamento_inf,
            sem_material=peca.sem_material,
            created_at=peca.created_at,
            updated_at=peca.updated_at,
        )
