"""Repository for budget reads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Cliente, Orcamento, OrcamentoVersao


@dataclass(frozen=True)
class OrcamentoResumo:
    """Read model for listing budget versions in the UI."""

    orcamento_id: int
    orcamento_versao_id: int
    ano: int
    num_orcamento: str
    numero_versao: int
    codigo_versao: str
    cliente_nome: str
    obra: str | None
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None
    estado: str
    preco_total: Decimal | None
    created_at: datetime


@dataclass(frozen=True)
class OrcamentoCriado:
    """Result of creating a simple budget."""

    ano: int
    num_orcamento: str
    numero_versao: int
    codigo_versao: str
    cliente_nome: str


class OrcamentoRepository:
    """Repository for Orcamento read operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_orcamentos(self) -> list[OrcamentoResumo]:
        """List budget versions with customer and budget data."""
        statement = (
            self._select_orcamento_resumo()
            .order_by(
                Orcamento.ano.desc(),
                Orcamento.num_orcamento.desc(),
                OrcamentoVersao.numero_versao.desc(),
            )
        )

        rows = self.session.execute(statement).mappings().all()

        return [self._row_to_orcamento_resumo(row) for row in rows]

    def get_orcamento_by_versao_id(self, orcamento_versao_id: int) -> OrcamentoResumo | None:
        """Return one budget version summary by version id."""
        statement = self._select_orcamento_resumo().where(OrcamentoVersao.id == orcamento_versao_id)
        row = self.session.execute(statement).mappings().one_or_none()

        if row is None:
            return None

        return self._row_to_orcamento_resumo(row)

    def get_next_num_orcamento(self, ano: int) -> str:
        """Return the next budget number for a year."""
        statement = select(Orcamento.num_orcamento).where(Orcamento.ano == ano)
        existing_numbers = self.session.execute(statement).scalars().all()

        numeric_numbers = [
            int(str(value))
            for value in existing_numbers
            if str(value).isdigit()
        ]

        if numeric_numbers:
            return str(max(numeric_numbers) + 1)

        return f"{ano % 100:02d}0001"

    def create_orcamento_com_versao_01(
        self,
        *,
        ano: int,
        num_orcamento: str,
        nome_cliente: str,
        email_cliente: str | None,
        telefone_cliente: str | None,
        obra: str,
        descricao: str | None,
        localizacao: str | None,
        ref_cliente: str | None,
        created_by_id: int | None,
    ) -> OrcamentoCriado:
        """Create a simple budget with version 01."""
        cliente = self._get_or_create_cliente_temporario(
            nome_cliente=nome_cliente,
            email_cliente=email_cliente,
            telefone_cliente=telefone_cliente,
        )

        orcamento = Orcamento(
            ano=ano,
            num_orcamento=num_orcamento,
            cliente_id=cliente.id,
            descricao=descricao,
            obra=obra,
            localizacao=localizacao,
            ref_cliente=ref_cliente,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        self.session.add(orcamento)
        self.session.flush()

        codigo_versao = self._format_codigo_versao(num_orcamento, 1)
        versao = OrcamentoVersao(
            orcamento_id=orcamento.id,
            numero_versao=1,
            codigo_versao=codigo_versao,
            estado="rascunho",
            preco_total=Decimal("0"),
            preco_origem=Decimal("0"),
            is_locked=False,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        self.session.add(versao)
        self.session.flush()

        return OrcamentoCriado(
            ano=ano,
            num_orcamento=num_orcamento,
            numero_versao=versao.numero_versao,
            codigo_versao=codigo_versao,
            cliente_nome=cliente.nome,
        )

    def _get_or_create_cliente_temporario(
        self,
        *,
        nome_cliente: str,
        email_cliente: str | None,
        telefone_cliente: str | None,
    ) -> Cliente:
        """Create or reuse a temporary customer."""
        if email_cliente:
            cliente = self.session.execute(
                select(Cliente).where(Cliente.email == email_cliente)
            ).scalar_one_or_none()
        else:
            cliente = self.session.execute(
                select(Cliente).where(
                    Cliente.nome == nome_cliente,
                    Cliente.is_temporary.is_(True),
                )
            ).scalar_one_or_none()

        if cliente is not None:
            return cliente

        cliente = Cliente(
            nome=nome_cliente,
            email=email_cliente,
            telefone=telefone_cliente,
            source_system="manual",
            is_temporary=True,
        )
        self.session.add(cliente)
        self.session.flush()

        return cliente

    def _format_codigo_versao(self, num_orcamento: str, numero_versao: int) -> str:
        """Format a budget version code."""
        return f"{num_orcamento}_{numero_versao:02d}"

    def _select_orcamento_resumo(self):
        """Build the base summary select used by listings and detail refresh."""
        return (
            select(
                Orcamento.id.label("orcamento_id"),
                OrcamentoVersao.id.label("orcamento_versao_id"),
                Orcamento.ano.label("ano"),
                Orcamento.num_orcamento.label("num_orcamento"),
                OrcamentoVersao.numero_versao.label("numero_versao"),
                OrcamentoVersao.codigo_versao.label("codigo_versao"),
                Cliente.nome.label("cliente_nome"),
                Orcamento.obra.label("obra"),
                Orcamento.descricao.label("descricao"),
                Orcamento.localizacao.label("localizacao"),
                Orcamento.ref_cliente.label("ref_cliente"),
                OrcamentoVersao.estado.label("estado"),
                OrcamentoVersao.preco_total.label("preco_total"),
                OrcamentoVersao.created_at.label("created_at"),
            )
            .join(Orcamento, OrcamentoVersao.orcamento_id == Orcamento.id)
            .join(Cliente, Orcamento.cliente_id == Cliente.id)
        )

    def _row_to_orcamento_resumo(self, row: Mapping[str, Any]) -> OrcamentoResumo:
        """Convert a database row mapping into the UI read model."""
        return OrcamentoResumo(
            orcamento_id=row["orcamento_id"],
            orcamento_versao_id=row["orcamento_versao_id"],
            ano=row["ano"],
            num_orcamento=row["num_orcamento"],
            numero_versao=row["numero_versao"],
            codigo_versao=row["codigo_versao"],
            cliente_nome=row["cliente_nome"],
            obra=row["obra"],
            descricao=row["descricao"],
            localizacao=row["localizacao"],
            ref_cliente=row["ref_cliente"],
            estado=row["estado"],
            preco_total=row["preco_total"],
            created_at=row["created_at"],
        )
