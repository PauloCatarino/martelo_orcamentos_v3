"""Repository for customer list reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cliente


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
    """Repository for customer read operations."""

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
