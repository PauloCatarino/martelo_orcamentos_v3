"""Repository for budget reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cliente, Orcamento, OrcamentoVersao


@dataclass(frozen=True)
class OrcamentoResumo:
    """Read model for listing budget versions in the UI."""

    ano: int
    num_orcamento: str
    numero_versao: int
    cliente_nome: str
    obra: str | None
    estado: str
    preco_total: Decimal | None
    created_at: datetime


class OrcamentoRepository:
    """Repository for Orcamento read operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_orcamentos(self) -> list[OrcamentoResumo]:
        """List budget versions with customer and budget data."""
        statement = (
            select(
                Orcamento.ano.label("ano"),
                Orcamento.num_orcamento.label("num_orcamento"),
                OrcamentoVersao.numero_versao.label("numero_versao"),
                Cliente.nome.label("cliente_nome"),
                Orcamento.obra.label("obra"),
                OrcamentoVersao.estado.label("estado"),
                OrcamentoVersao.preco_total.label("preco_total"),
                OrcamentoVersao.created_at.label("created_at"),
            )
            .join(Orcamento, OrcamentoVersao.orcamento_id == Orcamento.id)
            .join(Cliente, Orcamento.cliente_id == Cliente.id)
            .order_by(
                Orcamento.ano.desc(),
                Orcamento.num_orcamento.desc(),
                OrcamentoVersao.numero_versao.desc(),
            )
        )

        rows = self.session.execute(statement).mappings().all()

        return [
            OrcamentoResumo(
                ano=row["ano"],
                num_orcamento=row["num_orcamento"],
                numero_versao=row["numero_versao"],
                cliente_nome=row["cliente_nome"],
                obra=row["obra"],
                estado=row["estado"],
                preco_total=row["preco_total"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
