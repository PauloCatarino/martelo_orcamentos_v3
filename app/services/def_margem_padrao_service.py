"""Service for default-margin workflows (phase 8T.1).

Default margins are only the INITIAL values copied into new budget versions;
inside each budget the user keeps editing the version margins freely.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.margens_padrao_types import (
    AMBITO_CLIENTE,
    AMBITO_STANDARD,
    AMBITO_UTILIZADOR,
    normalize_ambito,
)
from app.domain.precos import MargensOrcamento
from app.repositories.def_margem_padrao_repository import (
    ClienteRef,
    DefMargemPadraoRepository,
    DefMargemPadraoResumo,
    UserRef,
)

# Resolution origins reported by resolver_margens_padrao.
ORIGEM_CLIENTE = "cliente"
ORIGEM_UTILIZADOR = "utilizador"
ORIGEM_STANDARD = "standard"
ORIGEM_ZEROS = "zeros"


@dataclass(frozen=True)
class CriarMargemPadraoData:
    """Input data for creating a default-margin record."""

    ambito: str
    cliente_id: int | None = None
    user_id: int | None = None
    margem_lucro_pct: Decimal = Decimal("0")
    margem_mp_pct: Decimal = Decimal("0")
    margem_mao_obra_pct: Decimal = Decimal("0")
    margem_acabamentos_pct: Decimal = Decimal("0")
    custos_administrativos_pct: Decimal = Decimal("0")
    ativo: bool = True


@dataclass(frozen=True)
class EditarMargemPadraoData:
    """Input data for editing the margin values of a record."""

    margem_lucro_pct: Decimal = Decimal("0")
    margem_mp_pct: Decimal = Decimal("0")
    margem_mao_obra_pct: Decimal = Decimal("0")
    margem_acabamentos_pct: Decimal = Decimal("0")
    custos_administrativos_pct: Decimal = Decimal("0")


class DefMargemPadraoService:
    """Application service for DefMargemPadrao workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefMargemPadraoRepository(session)

    def listar_por_ambito(self, ambito: str) -> list[DefMargemPadraoResumo]:
        """List the records of one scope."""
        ambito_normalizado = self._validar_ambito(ambito)
        return self.repository.list_by_ambito(ambito_normalizado)

    def obter_standard(self) -> DefMargemPadraoResumo | None:
        """Return the STANDARD record, or None."""
        return self.repository.get_standard()

    def guardar_standard(self, data: EditarMargemPadraoData) -> DefMargemPadraoResumo:
        """Create or update the single STANDARD record (idempotent)."""
        registo = self.repository.get_standard()
        if registo is None:
            result = self.repository.create_margem(
                ambito=AMBITO_STANDARD,
                margem_lucro_pct=data.margem_lucro_pct,
                margem_mp_pct=data.margem_mp_pct,
                margem_mao_obra_pct=data.margem_mao_obra_pct,
                margem_acabamentos_pct=data.margem_acabamentos_pct,
                custos_administrativos_pct=data.custos_administrativos_pct,
            )
        else:
            result = self.repository.update_margens(
                id=registo.id,
                margem_lucro_pct=data.margem_lucro_pct,
                margem_mp_pct=data.margem_mp_pct,
                margem_mao_obra_pct=data.margem_mao_obra_pct,
                margem_acabamentos_pct=data.margem_acabamentos_pct,
                custos_administrativos_pct=data.custos_administrativos_pct,
            )
        self.session.commit()

        return result

    def criar(self, data: CriarMargemPadraoData) -> DefMargemPadraoResumo:
        """Create a record, enforcing one per scope/customer/user."""
        ambito = self._validar_ambito(data.ambito)

        cliente_id = data.cliente_id if ambito == AMBITO_CLIENTE else None
        user_id = data.user_id if ambito == AMBITO_UTILIZADOR else None

        if ambito == AMBITO_STANDARD and self.repository.get_standard() is not None:
            raise ValueError("ja existe um registo STANDARD")
        if ambito == AMBITO_CLIENTE:
            if cliente_id is None:
                raise ValueError("cliente_id e obrigatorio no ambito CLIENTE")
            if self.repository.get_by_cliente(cliente_id) is not None:
                raise ValueError("ja existe um registo de margens para este cliente")
        if ambito == AMBITO_UTILIZADOR:
            if user_id is None:
                raise ValueError("user_id e obrigatorio no ambito UTILIZADOR")
            if self.repository.get_by_user(user_id) is not None:
                raise ValueError("ja existe um registo de margens para este utilizador")

        result = self.repository.create_margem(
            ambito=ambito,
            cliente_id=cliente_id,
            user_id=user_id,
            margem_lucro_pct=data.margem_lucro_pct,
            margem_mp_pct=data.margem_mp_pct,
            margem_mao_obra_pct=data.margem_mao_obra_pct,
            margem_acabamentos_pct=data.margem_acabamentos_pct,
            custos_administrativos_pct=data.custos_administrativos_pct,
            ativo=data.ativo,
        )
        self.session.commit()

        return result

    def editar(self, id: int, data: EditarMargemPadraoData) -> DefMargemPadraoResumo:
        """Edit the margin values of one record."""
        result = self.repository.update_margens(
            id=id,
            margem_lucro_pct=data.margem_lucro_pct,
            margem_mp_pct=data.margem_mp_pct,
            margem_mao_obra_pct=data.margem_mao_obra_pct,
            margem_acabamentos_pct=data.margem_acabamentos_pct,
            custos_administrativos_pct=data.custos_administrativos_pct,
        )
        self.session.commit()

        return result

    def definir_ativo(self, id: int, ativo: bool) -> DefMargemPadraoResumo:
        """Activate/deactivate one record."""
        result = self.repository.set_ativo(id, ativo)
        self.session.commit()

        return result

    def margens_cliente_por_contacto(
        self, nome: str | None, email: str | None
    ) -> MargensOrcamento | None:
        """Active customer margins for the customer a new budget would use.

        Mirrors the budget-creation customer matching (email first, then name
        among temporary customers); None when there is no applicable record.
        """
        cliente_id = self.repository.find_cliente_id_por_contacto(nome, email)
        if cliente_id is None:
            return None

        return self.repository.get_margens_ativas_por_cliente(cliente_id)

    def margens_utilizador(self, user_id: int | None) -> MargensOrcamento | None:
        """Active margins of one user, or None."""
        if user_id is None:
            return None

        return self.repository.get_margens_ativas_por_user(user_id)

    def margens_cliente(self, cliente_id: int | None) -> MargensOrcamento | None:
        """Active margins of one customer, or None."""
        if cliente_id is None:
            return None

        return self.repository.get_margens_ativas_por_cliente(cliente_id)

    def margens_standard(self) -> MargensOrcamento | None:
        """Active STANDARD margins, or None."""
        return self.repository.get_margens_ativas_standard()

    def resolver_margens_padrao(
        self, cliente_id: int | None, user_id: int | None
    ) -> tuple[MargensOrcamento, str]:
        """Resolve the default set: cliente -> utilizador -> standard -> zeros.

        Returns (margens, origem) with origem in 'cliente'/'utilizador'/
        'standard'/'zeros' so the caller can report what was applied.
        """
        if cliente_id is not None:
            margens = self.repository.get_margens_ativas_por_cliente(cliente_id)
            if margens is not None:
                return margens, ORIGEM_CLIENTE

        if user_id is not None:
            margens = self.repository.get_margens_ativas_por_user(user_id)
            if margens is not None:
                return margens, ORIGEM_UTILIZADOR

        margens = self.repository.get_margens_ativas_standard()
        if margens is not None:
            return margens, ORIGEM_STANDARD

        return MargensOrcamento(), ORIGEM_ZEROS

    def listar_clientes(self) -> list[ClienteRef]:
        """List customers for the per-customer combo."""
        return self.repository.list_clientes()

    def listar_utilizadores_ativos(self) -> list[UserRef]:
        """List active users for the per-user combo."""
        return self.repository.list_users_ativos()

    def _validar_ambito(self, ambito: str) -> str:
        """Validate and normalize a scope value."""
        normalizado = normalize_ambito(ambito)
        if normalizado is None:
            raise ValueError("ambito invalido")

        return normalizado
