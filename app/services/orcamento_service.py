"""Service for budget read workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.domain.margens_padrao_types import (
    AMBITO_CLIENTE,
    AMBITO_CLIENTE_FINAL,
    AMBITO_STANDARD,
    AMBITO_UTILIZADOR,
    normalizar_perfil_margens,
    normalize_ambito,
)
from app.domain.orcamento_estados import ESTADOS_ORCAMENTO
from app.domain.precos import MargensOrcamento
from app.models.orcamento_versao import OrcamentoVersao
from app.repositories.def_margem_padrao_repository import DefMargemPadraoRepository
from app.repositories.orcamento_repository import (
    ClienteResumo,
    OrcamentoCriado,
    OrcamentoRepository,
    OrcamentoResumo,
    OrcamentoVersaoCriada,
)
from app.services.orcamento_encomenda_phc_service import (
    EncomendaPhcInput,
    OrcamentoEncomendaPhcService,
)
from app.services.orcamento_historico_service import OrcamentoHistoricoService


@dataclass(frozen=True)
class CriarOrcamentoSimplesData:
    """Input data for creating a simple budget."""

    cliente_id: int
    obra: str
    descricao: str | None
    localizacao: str | None
    ref_cliente: str | None
    created_by_id: int | None = None
    enc_phc: str | None = None
    info_1: str | None = None
    info_2: str | None = None
    ano: int | None = None
    # Initial-margins choice: 'STANDARD' / 'CLIENTE' / 'UTILIZADOR' (phase 8T.1).
    margens_escolha: str = AMBITO_STANDARD


@dataclass(frozen=True)
class EditarOrcamentoData:
    """Input data for editing a budget's general data (phase 9.0)."""

    descricao: str | None
    obra: str
    localizacao: str | None
    ref_cliente: str | None
    estado: str
    enc_phc: str | None = None
    info_1: str | None = None
    info_2: str | None = None
    utilizador_id: int | None = None
    cliente_id: int | None = None
    # Phase 5: full set of PHC orders for the version. None keeps the legacy
    # behaviour of treating ``enc_phc`` as the single (principal) order.
    encomendas_phc: tuple[EncomendaPhcInput, ...] | None = None


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

    def find_orcamentos_por_ref_cliente(
        self, ref_cliente: str
    ) -> list[OrcamentoResumo]:
        """Find budget versions with the same customer reference."""
        return self.repository.find_by_ref_cliente(ref_cliente)

    def get_cliente_da_versao(
        self, orcamento_versao_id: int
    ) -> ClienteResumo | None:
        """Return the customer details of a budget version (for the report)."""
        return self.repository.get_cliente_da_versao(orcamento_versao_id)

    def criar_orcamento_simples(self, data: CriarOrcamentoSimplesData) -> OrcamentoCriado:
        """Create a simple budget with version 01."""
        obra = (data.obra or "").strip()

        if data.cliente_id is None:
            raise ValueError("cliente_id is required")

        ano = data.ano or date.today().year
        num_orcamento = self.repository.get_next_num_orcamento(ano)

        result = self.repository.create_orcamento_com_versao_01(
            ano=ano,
            num_orcamento=num_orcamento,
            cliente_id=data.cliente_id,
            obra=obra,
            descricao=data.descricao,
            localizacao=data.localizacao,
            ref_cliente=data.ref_cliente,
            created_by_id=data.created_by_id,
            enc_phc=data.enc_phc,
            info_1=data.info_1,
            info_2=data.info_2,
            margens=self._resolver_margens_iniciais(data),
            perfil_margens=normalizar_perfil_margens(data.margens_escolha),
        )
        enc_phc = (data.enc_phc or "").strip()
        if enc_phc and result.orcamento_versao_id is not None:
            OrcamentoEncomendaPhcService(self.session).substituir_encomendas(
                result.orcamento_versao_id,
                [EncomendaPhcInput(numero=enc_phc, is_principal=True)],
            )
        self.session.commit()

        return result

    def editar_orcamento(
        self,
        orcamento_id: int,
        data: EditarOrcamentoData,
        updated_by_id: int | None = None,
        *,
        orcamento_versao_id: int,
    ) -> bool:
        """Edit a budget's general data."""
        obra = (data.obra or "").strip()

        if data.estado not in ESTADOS_ORCAMENTO:
            raise ValueError("Estado inv\u00e1lido.")

        versao_atual = self.session.get(OrcamentoVersao, orcamento_versao_id)
        estado_anterior = versao_atual.estado if versao_atual is not None else None

        result = self.repository.update_orcamento(
            orcamento_id,
            descricao=data.descricao,
            obra=obra,
            localizacao=data.localizacao,
            ref_cliente=data.ref_cliente,
            info_1=data.info_1,
            info_2=data.info_2,
            updated_by_id=updated_by_id,
        )
        if versao_atual is None:
            enc_phc_result = False
        else:
            if data.encomendas_phc is not None:
                encomendas = list(data.encomendas_phc)
            elif data.enc_phc and data.enc_phc.strip():
                encomendas = [
                    EncomendaPhcInput(numero=data.enc_phc, is_principal=True)
                ]
            else:
                encomendas = []
            OrcamentoEncomendaPhcService(self.session).substituir_encomendas(
                orcamento_versao_id,
                encomendas,
            )
            enc_phc_result = True
        estado_result = self.repository.update_estado(
            orcamento_versao_id,
            data.estado,
        )
        utilizador_result = self.repository.update_utilizador(
            orcamento_versao_id,
            data.utilizador_id,
        )
        cliente_result = True
        if data.cliente_id is not None:
            cliente_result = self.repository.update_cliente(
                orcamento_id,
                data.cliente_id,
            )
        if estado_anterior is not None and estado_anterior != data.estado:
            OrcamentoHistoricoService(self.session).registar(
                orcamento_versao_id,
                "estado",
                f"Estado: {estado_anterior} \u2192 {data.estado}",
            )
        self.session.commit()

        return (
            result
            and enc_phc_result
            and estado_result
            and utilizador_result
            and cliente_result
        )

    def duplicar_versao(
        self, orcamento_versao_id: int, created_by_id: int | None = None
    ) -> OrcamentoVersaoCriada:
        """Create the next version of a budget, inheriting the source margins."""
        result = self.repository.duplicar_versao_profunda(
            orcamento_versao_id, created_by_id=created_by_id
        )
        OrcamentoHistoricoService(self.session).registar(
            result.orcamento_versao_id,
            "versao",
            f"Vers\u00e3o {result.codigo_versao} criada (duplicada)",
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
            if data.cliente_id is None:
                return None
            return self.margens_repository.get_margens_ativas_por_cliente(
                data.cliente_id
            )

        if escolha == AMBITO_CLIENTE_FINAL:
            return self.margens_repository.get_margens_ativas_cliente_final()

        if escolha == AMBITO_UTILIZADOR:
            if data.created_by_id is None:
                return None
            return self.margens_repository.get_margens_ativas_por_user(
                data.created_by_id
            )

        return self.margens_repository.get_margens_ativas_standard()
