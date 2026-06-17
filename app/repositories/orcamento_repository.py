"""Repository for budget reads."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.precos import MargensOrcamento
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
class ClienteResumo:
    """Read model for the customer block of a budget report (phase 8W.1)."""

    id: int
    nome: str
    nome_simplex: str | None
    morada: str | None
    email: str | None
    telefone: str | None
    num_cliente: str | None


@dataclass(frozen=True)
class OrcamentoCriado:
    """Result of creating a simple budget."""

    ano: int
    num_orcamento: str
    numero_versao: int
    codigo_versao: str
    cliente_nome: str


@dataclass(frozen=True)
class OrcamentoVersaoCriada:
    """Result of duplicating a budget version."""

    orcamento_id: int
    orcamento_versao_id: int
    numero_versao: int
    codigo_versao: str


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
        margens: MargensOrcamento | None = None,
    ) -> OrcamentoCriado:
        """Create a simple budget with version 01.

        ``margens`` are the initial margin values copied into the version;
        None keeps the column defaults (zeros).
        """
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
        if margens is not None:
            self._aplicar_margens_versao(versao, margens)
        self.session.add(versao)
        self.session.flush()

        return OrcamentoCriado(
            ano=ano,
            num_orcamento=num_orcamento,
            numero_versao=versao.numero_versao,
            codigo_versao=codigo_versao,
            cliente_nome=cliente.nome,
        )

    def criar_nova_versao(
        self,
        orcamento_versao_id: int,
        created_by_id: int | None = None,
    ) -> OrcamentoVersaoCriada:
        """Duplicate a budget version header into the next version number.

        The new version starts as 'rascunho' with zero total (items are not
        copied here) and INHERITS the source version's margins and production
        default; preco_origem records the source version's total.
        """
        origem = self.session.get(OrcamentoVersao, orcamento_versao_id)
        if origem is None:
            raise ValueError("orcamento_versao not found")

        proximo_numero = self.session.execute(
            select(func.coalesce(func.max(OrcamentoVersao.numero_versao), 0)).where(
                OrcamentoVersao.orcamento_id == origem.orcamento_id
            )
        ).scalar_one() + 1

        orcamento = self.session.get(Orcamento, origem.orcamento_id)
        codigo_versao = self._format_codigo_versao(
            orcamento.num_orcamento, proximo_numero
        )
        versao = OrcamentoVersao(
            orcamento_id=origem.orcamento_id,
            numero_versao=proximo_numero,
            codigo_versao=codigo_versao,
            estado="rascunho",
            preco_total=Decimal("0"),
            preco_origem=origem.preco_total,
            tipo_producao_default=origem.tipo_producao_default,
            is_locked=False,
            created_by_id=created_by_id,
            updated_by_id=created_by_id,
        )
        self._aplicar_margens_versao(
            versao,
            MargensOrcamento(
                margem_lucro_pct=origem.margem_lucro_pct,
                margem_mp_pct=origem.margem_mp_pct,
                margem_mao_obra_pct=origem.margem_mao_obra_pct,
                margem_acabamentos_pct=origem.margem_acabamentos_pct,
                custos_administrativos_pct=origem.custos_administrativos_pct,
            ),
        )
        self.session.add(versao)
        self.session.flush()

        return OrcamentoVersaoCriada(
            orcamento_id=versao.orcamento_id,
            orcamento_versao_id=versao.id,
            numero_versao=versao.numero_versao,
            codigo_versao=versao.codigo_versao,
        )

    def get_cliente_id_by_versao(self, orcamento_versao_id: int) -> int | None:
        """Return the customer id of one budget version (or None)."""
        statement = (
            select(Orcamento.cliente_id)
            .join(OrcamentoVersao, OrcamentoVersao.orcamento_id == Orcamento.id)
            .where(OrcamentoVersao.id == orcamento_versao_id)
        )
        return self.session.execute(statement).scalars().first()

    def get_cliente_da_versao(self, orcamento_versao_id: int) -> ClienteResumo | None:
        """Return the customer details of one budget version (for the report)."""
        statement = (
            select(Cliente)
            .join(Orcamento, Orcamento.cliente_id == Cliente.id)
            .join(OrcamentoVersao, OrcamentoVersao.orcamento_id == Orcamento.id)
            .where(OrcamentoVersao.id == orcamento_versao_id)
        )
        cliente = self.session.execute(statement).scalars().first()
        if cliente is None:
            return None

        return ClienteResumo(
            id=cliente.id,
            nome=cliente.nome,
            nome_simplex=cliente.nome_simplex,
            morada=cliente.morada,
            email=cliente.email,
            telefone=cliente.telefone or cliente.telemovel,
            num_cliente=cliente.num_cliente_phc,
        )

    @staticmethod
    def _aplicar_margens_versao(
        versao: OrcamentoVersao, margens: MargensOrcamento
    ) -> None:
        """Copy margin values into a budget version."""
        versao.margem_lucro_pct = margens.margem_lucro_pct
        versao.margem_mp_pct = margens.margem_mp_pct
        versao.margem_mao_obra_pct = margens.margem_mao_obra_pct
        versao.margem_acabamentos_pct = margens.margem_acabamentos_pct
        versao.custos_administrativos_pct = margens.custos_administrativos_pct

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
