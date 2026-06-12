"""Service for budget read workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.domain.margens_padrao_types import (
    AMBITO_CLIENTE,
    AMBITO_STANDARD,
    AMBITO_UTILIZADOR,
    normalize_ambito,
)
from app.domain.precos import MargensOrcamento
from app.repositories.def_margem_padrao_repository import DefMargemPadraoRepository
from app.repositories.orcamento_repository import (
    OrcamentoCriado,
    OrcamentoRepository,
    OrcamentoResumo,
    OrcamentoVersaoCriada,
)


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
    # Initial-margins choice: 'STANDARD' / 'CLIENTE' / 'UTILIZADOR' (phase 8T.1).
    margens_escolha: str = AMBITO_STANDARD


class OrcamentoService:
    """Application service for Orcamento workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoRepository(session)
        self.margens_repository = DefMargemPadraoRepository(session)

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
            margens=self._resolver_margens_iniciais(data),
        )
        self.session.commit()

        return result

    def duplicar_versao(
        self, orcamento_versao_id: int, created_by_id: int | None = None
    ) -> OrcamentoVersaoCriada:
        """Create the next version of a budget, inheriting the source margins."""
        result = self.repository.criar_nova_versao(
            orcamento_versao_id, created_by_id=created_by_id
        )
        self.session.commit()

        return result

    def get_cliente_id_by_versao(self, orcamento_versao_id: int) -> int | None:
        """Return the customer id of one budget version (or None)."""
        return self.repository.get_cliente_id_by_versao(orcamento_versao_id)

    def _resolver_margens_iniciais(
        self, data: CriarOrcamentoSimplesData
    ) -> MargensOrcamento | None:
        """Resolve the initial margins for the chosen set.

        Returns None (column defaults = zeros) when the chosen set has no
        applicable active record.
        """
        escolha = normalize_ambito(data.margens_escolha) or AMBITO_STANDARD

        if escolha == AMBITO_CLIENTE:
            cliente_id = self.margens_repository.find_cliente_id_por_contacto(
                data.nome_cliente, data.email_cliente
            )
            if cliente_id is None:
                return None
            return self.margens_repository.get_margens_ativas_por_cliente(cliente_id)

        if escolha == AMBITO_UTILIZADOR:
            if data.created_by_id is None:
                return None
            return self.margens_repository.get_margens_ativas_por_user(
                data.created_by_id
            )

        return self.margens_repository.get_margens_ativas_standard()
