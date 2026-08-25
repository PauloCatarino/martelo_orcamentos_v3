"""Repository for supplier reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DefFornecedor, DefMateriaPrima


@dataclass(frozen=True)
class DefFornecedorResumo:
    """Read model for listing suppliers."""

    id: int
    nome: str
    email: str | None
    email_cc: str | None
    pessoa_contacto: str | None
    telefone: str | None
    observacoes: str | None
    ativo: bool
    #: Quantas matérias-primas ativas estão ligadas a este fornecedor.
    materias_primas: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def tem_email(self) -> bool:
        """Sem email não é possível pedir-lhe preços."""
        return bool((self.email or "").strip())


class DefFornecedorRepository:
    """Repository for DefFornecedor operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self, incluir_inativos: bool = True) -> list[DefFornecedorResumo]:
        """List suppliers with how many raw materials each one supplies."""
        contagem = (
            select(
                DefMateriaPrima.fornecedor_id.label("fornecedor_id"),
                func.count().label("total"),
            )
            .where(DefMateriaPrima.ativo.is_(True))
            .group_by(DefMateriaPrima.fornecedor_id)
            .subquery()
        )

        statement = (
            select(DefFornecedor, func.coalesce(contagem.c.total, 0))
            .join(contagem, contagem.c.fornecedor_id == DefFornecedor.id, isouter=True)
            .order_by(DefFornecedor.nome.asc())
        )
        if not incluir_inativos:
            statement = statement.where(DefFornecedor.ativo.is_(True))

        return [
            self._to_resumo(fornecedor, total)
            for fornecedor, total in self.session.execute(statement)
        ]

    def get_by_id(self, id: int) -> DefFornecedorResumo | None:
        """Get one supplier by id."""
        fornecedor = self.session.get(DefFornecedor, id)
        if fornecedor is None:
            return None

        return self._to_resumo(fornecedor)

    def get_by_nome(self, nome: str) -> DefFornecedorResumo | None:
        """Get one supplier by name (exact, trimmed)."""
        statement = select(DefFornecedor).where(DefFornecedor.nome == nome.strip())
        fornecedor = self.session.execute(statement).scalars().first()
        if fornecedor is None:
            return None

        return self._to_resumo(fornecedor)

    def create_fornecedor(
        self,
        *,
        nome: str,
        email: str | None = None,
        email_cc: str | None = None,
        pessoa_contacto: str | None = None,
        telefone: str | None = None,
        observacoes: str | None = None,
        ativo: bool = True,
    ) -> DefFornecedorResumo:
        """Create one supplier."""
        fornecedor = DefFornecedor(
            nome=nome,
            email=email,
            email_cc=email_cc,
            pessoa_contacto=pessoa_contacto,
            telefone=telefone,
            observacoes=observacoes,
            ativo=ativo,
        )
        self.session.add(fornecedor)
        self.session.flush()

        return self._to_resumo(fornecedor)

    def update_fornecedor(
        self,
        *,
        id: int,
        nome: str,
        email: str | None = None,
        email_cc: str | None = None,
        pessoa_contacto: str | None = None,
        telefone: str | None = None,
        observacoes: str | None = None,
        ativo: bool = True,
    ) -> DefFornecedorResumo:
        """Update one supplier."""
        fornecedor = self.session.get(DefFornecedor, id)
        if fornecedor is None:
            raise ValueError("def_fornecedor not found")

        fornecedor.nome = nome
        fornecedor.email = email
        fornecedor.email_cc = email_cc
        fornecedor.pessoa_contacto = pessoa_contacto
        fornecedor.telefone = telefone
        fornecedor.observacoes = observacoes
        fornecedor.ativo = ativo
        self.session.flush()

        return self._to_resumo(fornecedor)

    def _to_resumo(
        self, fornecedor: DefFornecedor, materias_primas: int = 0
    ) -> DefFornecedorResumo:
        """Convert an ORM supplier to the read model."""
        return DefFornecedorResumo(
            id=fornecedor.id,
            nome=fornecedor.nome,
            email=fornecedor.email,
            email_cc=fornecedor.email_cc,
            pessoa_contacto=fornecedor.pessoa_contacto,
            telefone=fornecedor.telefone,
            observacoes=fornecedor.observacoes,
            ativo=fornecedor.ativo,
            materias_primas=materias_primas,
            created_at=fornecedor.created_at,
            updated_at=fornecedor.updated_at,
        )
