"""Service for budget read workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.repositories.orcamento_repository import OrcamentoCriado, OrcamentoRepository, OrcamentoResumo


@dataclass(frozen=True)
class CriarOrcamentoSimplesData:
    """Input data for creating a simple budget."""

    nome_cliente: str
    email_cliente: str | None
    telefone_cliente: str | None
    obra: str
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None
    created_by_id: int | None = None
    ano: int | None = None


class OrcamentoService:
    """Application service for Orcamento workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoRepository(session)

    def list_orcamentos(self) -> list[OrcamentoResumo]:
        """List available budget versions."""
        return self.repository.list_orcamentos()

    def get_orcamento_by_versao_id(self, orcamento_versao_id: int) -> OrcamentoResumo | None:
        """Return one budget version by id."""
        return self.repository.get_orcamento_by_versao_id(orcamento_versao_id)

    def criar_orcamento_simples(self, data: CriarOrcamentoSimplesData) -> OrcamentoCriado:
        """Create a simple budget with version 01."""
        nome_cliente = data.nome_cliente.strip()
        obra = data.obra.strip()

        if not nome_cliente:
            raise ValueError("nome_cliente is required")

        if not obra:
            raise ValueError("obra is required")

        ano = data.ano or date.today().year
        num_orcamento = self.repository.get_next_num_orcamento(ano)

        result = self.repository.create_orcamento_com_versao_01(
            ano=ano,
            num_orcamento=num_orcamento,
            nome_cliente=nome_cliente,
            email_cliente=data.email_cliente,
            telefone_cliente=data.telefone_cliente,
            obra=obra,
            descricao=data.descricao,
            localizacao=data.localizacao,
            ref_cliente=data.ref_cliente,
            created_by_id=data.created_by_id,
        )
        self.session.commit()

        return result
