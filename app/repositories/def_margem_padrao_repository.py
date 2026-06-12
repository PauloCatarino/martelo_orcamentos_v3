"""Repository for default-margin reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.margens_padrao_types import (
    AMBITO_CLIENTE,
    AMBITO_STANDARD,
    AMBITO_UTILIZADOR,
)
from app.domain.precos import MargensOrcamento
from app.models import Cliente, DefMargemPadrao, User


@dataclass(frozen=True)
class DefMargemPadraoResumo:
    """Read model for default-margin records."""

    id: int
    ambito: str
    cliente_id: int | None
    user_id: int | None
    margem_lucro_pct: Decimal
    margem_mp_pct: Decimal
    margem_mao_obra_pct: Decimal
    margem_acabamentos_pct: Decimal
    custos_administrativos_pct: Decimal
    ativo: bool
    cliente_nome: str | None = None
    user_nome: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_margens(self) -> MargensOrcamento:
        """Convert the record into the budget-version margins value."""
        return MargensOrcamento(
            margem_lucro_pct=self.margem_lucro_pct,
            margem_mp_pct=self.margem_mp_pct,
            margem_mao_obra_pct=self.margem_mao_obra_pct,
            margem_acabamentos_pct=self.margem_acabamentos_pct,
            custos_administrativos_pct=self.custos_administrativos_pct,
        )


@dataclass(frozen=True)
class ClienteRef:
    """Minimal customer reference for combos."""

    id: int
    nome: str
    email: str | None = None


@dataclass(frozen=True)
class UserRef:
    """Minimal user reference for combos."""

    id: int
    nome: str
    username: str | None = None


class DefMargemPadraoRepository:
    """Repository for DefMargemPadrao operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_ambito(self, ambito: str) -> list[DefMargemPadraoResumo]:
        """List the records of one scope (with customer/user names)."""
        statement = (
            select(DefMargemPadrao)
            .where(DefMargemPadrao.ambito == ambito)
            .order_by(DefMargemPadrao.id.asc())
        )
        registos = self.session.execute(statement).scalars().all()

        return [self._to_resumo(registo) for registo in registos]

    def get_by_id(self, id: int) -> DefMargemPadraoResumo | None:
        """Get one record by id."""
        registo = self.session.get(DefMargemPadrao, id)
        if registo is None:
            return None

        return self._to_resumo(registo)

    def get_standard(self) -> DefMargemPadraoResumo | None:
        """Return the STANDARD record (active or not), or None."""
        statement = (
            select(DefMargemPadrao)
            .where(DefMargemPadrao.ambito == AMBITO_STANDARD)
            .order_by(DefMargemPadrao.id.asc())
        )
        registo = self.session.execute(statement).scalars().first()
        if registo is None:
            return None

        return self._to_resumo(registo)

    def get_by_cliente(self, cliente_id: int) -> DefMargemPadraoResumo | None:
        """Return the customer's record (active or not), or None."""
        statement = select(DefMargemPadrao).where(
            DefMargemPadrao.ambito == AMBITO_CLIENTE,
            DefMargemPadrao.cliente_id == cliente_id,
        )
        registo = self.session.execute(statement).scalars().first()
        if registo is None:
            return None

        return self._to_resumo(registo)

    def get_by_user(self, user_id: int) -> DefMargemPadraoResumo | None:
        """Return the user's record (active or not), or None."""
        statement = select(DefMargemPadrao).where(
            DefMargemPadrao.ambito == AMBITO_UTILIZADOR,
            DefMargemPadrao.user_id == user_id,
        )
        registo = self.session.execute(statement).scalars().first()
        if registo is None:
            return None

        return self._to_resumo(registo)

    def get_margens_ativas_standard(self) -> MargensOrcamento | None:
        """Margins of the active STANDARD record, or None."""
        registo = self.get_standard()
        if registo is None or not registo.ativo:
            return None

        return registo.to_margens()

    def get_margens_ativas_por_cliente(self, cliente_id: int) -> MargensOrcamento | None:
        """Margins of the customer's active record, or None."""
        registo = self.get_by_cliente(cliente_id)
        if registo is None or not registo.ativo:
            return None

        return registo.to_margens()

    def get_margens_ativas_por_user(self, user_id: int) -> MargensOrcamento | None:
        """Margins of the user's active record, or None."""
        registo = self.get_by_user(user_id)
        if registo is None or not registo.ativo:
            return None

        return registo.to_margens()

    def find_cliente_id_por_contacto(
        self, nome: str | None, email: str | None
    ) -> int | None:
        """Find the customer a new budget would attach to (no creation).

        Mirrors the matching used when creating a budget: by email first (any
        customer), else by name among temporary customers. Returns None when
        the budget would create a new customer.
        """
        email_normalizado = (email or "").strip()
        if email_normalizado:
            cliente_id = self.session.execute(
                select(Cliente.id).where(Cliente.email == email_normalizado)
            ).scalars().first()
            if cliente_id is not None:
                return cliente_id

        nome_normalizado = (nome or "").strip()
        if not nome_normalizado:
            return None

        return self.session.execute(
            select(Cliente.id).where(
                Cliente.nome == nome_normalizado,
                Cliente.is_temporary.is_(True),
            )
        ).scalars().first()

    def create_margem(
        self,
        *,
        ambito: str,
        cliente_id: int | None = None,
        user_id: int | None = None,
        margem_lucro_pct: Decimal = Decimal("0"),
        margem_mp_pct: Decimal = Decimal("0"),
        margem_mao_obra_pct: Decimal = Decimal("0"),
        margem_acabamentos_pct: Decimal = Decimal("0"),
        custos_administrativos_pct: Decimal = Decimal("0"),
        ativo: bool = True,
    ) -> DefMargemPadraoResumo:
        """Create one default-margin record."""
        registo = DefMargemPadrao(
            ambito=ambito,
            cliente_id=cliente_id,
            user_id=user_id,
            margem_lucro_pct=margem_lucro_pct,
            margem_mp_pct=margem_mp_pct,
            margem_mao_obra_pct=margem_mao_obra_pct,
            margem_acabamentos_pct=margem_acabamentos_pct,
            custos_administrativos_pct=custos_administrativos_pct,
            ativo=ativo,
        )
        self.session.add(registo)
        self.session.flush()

        return self._to_resumo(registo)

    def update_margens(
        self,
        *,
        id: int,
        margem_lucro_pct: Decimal,
        margem_mp_pct: Decimal,
        margem_mao_obra_pct: Decimal,
        margem_acabamentos_pct: Decimal,
        custos_administrativos_pct: Decimal,
    ) -> DefMargemPadraoResumo:
        """Update the margin values of one record."""
        registo = self.session.get(DefMargemPadrao, id)
        if registo is None:
            raise ValueError("registo de margens nao encontrado")

        registo.margem_lucro_pct = margem_lucro_pct
        registo.margem_mp_pct = margem_mp_pct
        registo.margem_mao_obra_pct = margem_mao_obra_pct
        registo.margem_acabamentos_pct = margem_acabamentos_pct
        registo.custos_administrativos_pct = custos_administrativos_pct
        self.session.flush()

        return self._to_resumo(registo)

    def set_ativo(self, id: int, ativo: bool) -> DefMargemPadraoResumo:
        """Activate/deactivate one record."""
        registo = self.session.get(DefMargemPadrao, id)
        if registo is None:
            raise ValueError("registo de margens nao encontrado")

        registo.ativo = ativo
        self.session.flush()

        return self._to_resumo(registo)

    def list_clientes(self) -> list[ClienteRef]:
        """List customers for the per-customer combo."""
        statement = select(Cliente).order_by(Cliente.nome.asc())
        clientes = self.session.execute(statement).scalars().all()

        return [
            ClienteRef(id=cliente.id, nome=cliente.nome, email=cliente.email)
            for cliente in clientes
        ]

    def list_users_ativos(self) -> list[UserRef]:
        """List active users for the per-user combo."""
        statement = (
            select(User).where(User.is_active.is_(True)).order_by(User.nome.asc())
        )
        users = self.session.execute(statement).scalars().all()

        return [
            UserRef(id=user.id, nome=user.nome, username=user.username)
            for user in users
        ]

    def _to_resumo(self, registo: DefMargemPadrao) -> DefMargemPadraoResumo:
        """Convert an ORM record to the read model."""
        return DefMargemPadraoResumo(
            id=registo.id,
            ambito=registo.ambito,
            cliente_id=registo.cliente_id,
            user_id=registo.user_id,
            margem_lucro_pct=registo.margem_lucro_pct,
            margem_mp_pct=registo.margem_mp_pct,
            margem_mao_obra_pct=registo.margem_mao_obra_pct,
            margem_acabamentos_pct=registo.margem_acabamentos_pct,
            custos_administrativos_pct=registo.custos_administrativos_pct,
            ativo=registo.ativo,
            cliente_nome=registo.cliente.nome if registo.cliente else None,
            user_nome=registo.user.nome if registo.user else None,
            created_at=registo.created_at,
            updated_at=registo.updated_at,
        )
