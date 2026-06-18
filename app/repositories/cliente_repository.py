"""Repository for customer list operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Cliente, Orcamento


@dataclass(frozen=True)
class ClienteListaResumo:
    """Read model for the customers list page."""

    id: int
    nome: str
    nome_simplex: str | None
    morada: str | None
    email: str | None
    pagina_web: str | None
    telefone: str | None
    telemovel: str | None
    num_cliente_phc: str | None
    info_1: str | None
    info_2: str | None
    is_temporary: bool
    created_at: datetime


class ClienteRepository:
    """Repository for customer list and temporary-customer write operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_temporarios(self) -> list[ClienteListaResumo]:
        """List temporary customers ordered by name."""
        rows = (
            self.session.execute(
                select(Cliente)
                .where(Cliente.is_temporary.is_(True))
                .order_by(Cliente.nome.asc())
            )
            .scalars()
            .all()
        )
        return [self._to_resumo(cliente) for cliente in rows]

    def list_phc(self) -> list[ClienteListaResumo]:
        """List PHC (official) customers ordered by name."""
        rows = (
            self.session.execute(
                select(Cliente)
                .where(Cliente.is_temporary.is_(False))
                .order_by(Cliente.nome.asc())
            )
            .scalars()
            .all()
        )
        return [self._to_resumo(cliente) for cliente in rows]

    def criar(
        self,
        *,
        nome: str,
        nome_simplex: str,
        morada: str | None,
        email: str | None,
        pagina_web: str | None,
        telefone: str | None,
        telemovel: str | None,
        num_cliente_phc: str | None,
        info_1: str | None,
        info_2: str | None,
    ) -> ClienteListaResumo:
        """Create a temporary customer."""
        cliente = Cliente(
            nome=nome,
            nome_simplex=nome_simplex,
            morada=morada,
            email=email,
            pagina_web=pagina_web,
            telefone=telefone,
            telemovel=telemovel,
            num_cliente_phc=num_cliente_phc,
            info_1=info_1,
            info_2=info_2,
            source_system="manual",
            is_temporary=True,
        )
        self.session.add(cliente)
        self.session.flush()

        return self._to_resumo(cliente)

    def atualizar(
        self,
        *,
        id: int,
        nome: str,
        nome_simplex: str,
        morada: str | None,
        email: str | None,
        pagina_web: str | None,
        telefone: str | None,
        telemovel: str | None,
        num_cliente_phc: str | None,
        info_1: str | None,
        info_2: str | None,
    ) -> ClienteListaResumo:
        """Update a temporary customer."""
        cliente = self.session.get(Cliente, id)
        if cliente is None or not cliente.is_temporary:
            raise ValueError("Cliente tempor\u00e1rio n\u00e3o encontrado.")

        cliente.nome = nome
        cliente.nome_simplex = nome_simplex
        cliente.morada = morada
        cliente.email = email
        cliente.pagina_web = pagina_web
        cliente.telefone = telefone
        cliente.telemovel = telemovel
        cliente.num_cliente_phc = num_cliente_phc
        cliente.info_1 = info_1
        cliente.info_2 = info_2
        self.session.flush()

        return self._to_resumo(cliente)

    def eliminar(self, id: int) -> None:
        """Delete a temporary customer."""
        cliente = self.session.get(Cliente, id)
        if cliente is None or not cliente.is_temporary:
            raise ValueError("Cliente tempor\u00e1rio n\u00e3o encontrado.")

        self.session.delete(cliente)

    def contar_orcamentos(self, cliente_id: int) -> int:
        """Count budgets associated with one customer."""
        return self.session.execute(
            select(func.count()).select_from(Orcamento).where(
                Orcamento.cliente_id == cliente_id
            )
        ).scalar_one()

    def _to_resumo(self, cliente: Cliente) -> ClienteListaResumo:
        """Convert a Cliente model into a list read model."""
        return ClienteListaResumo(
            id=cliente.id,
            nome=cliente.nome,
            nome_simplex=cliente.nome_simplex,
            morada=cliente.morada,
            email=cliente.email,
            pagina_web=cliente.pagina_web,
            telefone=cliente.telefone,
            telemovel=cliente.telemovel,
            num_cliente_phc=cliente.num_cliente_phc,
            info_1=cliente.info_1,
            info_2=cliente.info_2,
            is_temporary=cliente.is_temporary,
            created_at=cliente.created_at,
        )
