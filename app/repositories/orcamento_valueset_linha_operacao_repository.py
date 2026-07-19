"""Repository for budget version ValueSet line operation link reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import OrcamentoValuesetLinhaOperacao


@dataclass(frozen=True)
class OrcamentoValuesetLinhaOperacaoResumo:
    """Read model for operations associated with a budget version ValueSet line."""

    id: int
    orcamento_valueset_linha_id: int
    def_operacao_id: int
    ordem: int
    regra_calculo: str | None
    quantidade_base: Decimal | None
    obrigatorio: bool
    ativo: bool
    observacoes: str | None
    rasgo_qt_comp: int = 0
    rasgo_qt_larg: int = 0
    acao: str = "ADICIONAR"
    tempo_setup_minutos: Decimal | None = None
    tempo_por_unidade_minutos: Decimal | None = None
    unidade_tempo: str | None = None
    metodo_calculo: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrcamentoValuesetLinhaOperacaoRepository:
    """Repository for OrcamentoValuesetLinhaOperacao operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_linha(
        self, orcamento_valueset_linha_id: int
    ) -> list[OrcamentoValuesetLinhaOperacaoResumo]:
        """List operations linked to one budget version ValueSet line."""
        statement = (
            select(OrcamentoValuesetLinhaOperacao)
            .where(
                OrcamentoValuesetLinhaOperacao.orcamento_valueset_linha_id
                == orcamento_valueset_linha_id
            )
            .order_by(
                OrcamentoValuesetLinhaOperacao.ordem.asc(),
                OrcamentoValuesetLinhaOperacao.id.asc(),
            )
        )
        ligacoes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(ligacao) for ligacao in ligacoes]

    def list_active_by_linha(
        self, orcamento_valueset_linha_id: int
    ) -> list[OrcamentoValuesetLinhaOperacaoResumo]:
        """List active operations linked to one budget version ValueSet line."""
        statement = (
            select(OrcamentoValuesetLinhaOperacao)
            .where(
                OrcamentoValuesetLinhaOperacao.orcamento_valueset_linha_id
                == orcamento_valueset_linha_id,
                OrcamentoValuesetLinhaOperacao.ativo.is_(True),
            )
            .order_by(
                OrcamentoValuesetLinhaOperacao.ordem.asc(),
                OrcamentoValuesetLinhaOperacao.id.asc(),
            )
        )
        ligacoes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(ligacao) for ligacao in ligacoes]

    def get_by_id(self, id: int) -> OrcamentoValuesetLinhaOperacaoResumo | None:
        """Get one budget version ValueSet line operation link by id."""
        ligacao = self.session.get(OrcamentoValuesetLinhaOperacao, id)
        if ligacao is None:
            return None

        return self._to_resumo(ligacao)

    def create(
        self,
        *,
        orcamento_valueset_linha_id: int,
        def_operacao_id: int,
        ordem: int = 1,
        acao: str = "ADICIONAR",
        metodo_calculo: str | None = None,
        regra_calculo: str | None = None,
        quantidade_base: Decimal | None = None,
        rasgo_qt_comp: int = 0,
        rasgo_qt_larg: int = 0,
        tempo_setup_minutos: Decimal | None = None,
        tempo_por_unidade_minutos: Decimal | None = None,
        unidade_tempo: str | None = None,
        obrigatorio: bool = True,
        ativo: bool = True,
        observacoes: str | None = None,
    ) -> OrcamentoValuesetLinhaOperacaoResumo:
        """Create one budget version ValueSet line operation link."""
        ligacao = OrcamentoValuesetLinhaOperacao(
            orcamento_valueset_linha_id=orcamento_valueset_linha_id,
            def_operacao_id=def_operacao_id,
            ordem=ordem,
            acao=acao,
            metodo_calculo=metodo_calculo,
            regra_calculo=regra_calculo,
            quantidade_base=quantidade_base,
            rasgo_qt_comp=rasgo_qt_comp,
            rasgo_qt_larg=rasgo_qt_larg,
            tempo_setup_minutos=tempo_setup_minutos,
            tempo_por_unidade_minutos=tempo_por_unidade_minutos,
            unidade_tempo=unidade_tempo,
            obrigatorio=obrigatorio,
            ativo=ativo,
            observacoes=observacoes,
        )
        self.session.add(ligacao)
        self.session.flush()

        return self._to_resumo(ligacao)

    def update(
        self,
        *,
        id: int,
        orcamento_valueset_linha_id: int,
        def_operacao_id: int,
        ordem: int = 1,
        acao: str = "ADICIONAR",
        metodo_calculo: str | None = None,
        regra_calculo: str | None = None,
        quantidade_base: Decimal | None = None,
        rasgo_qt_comp: int = 0,
        rasgo_qt_larg: int = 0,
        tempo_setup_minutos: Decimal | None = None,
        tempo_por_unidade_minutos: Decimal | None = None,
        unidade_tempo: str | None = None,
        obrigatorio: bool = True,
        ativo: bool = True,
        observacoes: str | None = None,
    ) -> OrcamentoValuesetLinhaOperacaoResumo:
        """Update one budget version ValueSet line operation link."""
        ligacao = self.session.get(OrcamentoValuesetLinhaOperacao, id)
        if ligacao is None:
            raise ValueError("orcamento_valueset_linha_operacao not found")

        ligacao.orcamento_valueset_linha_id = orcamento_valueset_linha_id
        ligacao.def_operacao_id = def_operacao_id
        ligacao.ordem = ordem
        ligacao.acao = acao
        ligacao.metodo_calculo = metodo_calculo
        ligacao.regra_calculo = regra_calculo
        ligacao.quantidade_base = quantidade_base
        ligacao.rasgo_qt_comp = rasgo_qt_comp
        ligacao.rasgo_qt_larg = rasgo_qt_larg
        ligacao.tempo_setup_minutos = tempo_setup_minutos
        ligacao.tempo_por_unidade_minutos = tempo_por_unidade_minutos
        ligacao.unidade_tempo = unidade_tempo
        ligacao.obrigatorio = obrigatorio
        ligacao.ativo = ativo
        ligacao.observacoes = observacoes
        self.session.flush()

        return self._to_resumo(ligacao)

    def deactivate(self, id: int) -> bool:
        """Deactivate one budget version ValueSet line operation link."""
        ligacao = self.session.get(OrcamentoValuesetLinhaOperacao, id)
        if ligacao is None:
            return False

        ligacao.ativo = False
        self.session.flush()

        return True

    def activate(self, id: int) -> bool:
        """Reactivate one budget version ValueSet line operation link."""
        ligacao = self.session.get(OrcamentoValuesetLinhaOperacao, id)
        if ligacao is None:
            return False

        ligacao.ativo = True
        self.session.flush()

        return True

    def delete_by_linha(self, orcamento_valueset_linha_id: int) -> int:
        """Hard-delete all operations of one budget version ValueSet line."""
        result = self.session.execute(
            delete(OrcamentoValuesetLinhaOperacao)
            .where(
                OrcamentoValuesetLinhaOperacao.orcamento_valueset_linha_id
                == orcamento_valueset_linha_id
            )
            .execution_options(synchronize_session=False)
        )
        self.session.flush()
        return int(result.rowcount or 0)

    def _to_resumo(
        self, ligacao: OrcamentoValuesetLinhaOperacao
    ) -> OrcamentoValuesetLinhaOperacaoResumo:
        """Convert an ORM budget version ValueSet line operation link to read model."""
        return OrcamentoValuesetLinhaOperacaoResumo(
            id=ligacao.id,
            orcamento_valueset_linha_id=ligacao.orcamento_valueset_linha_id,
            def_operacao_id=ligacao.def_operacao_id,
            ordem=ligacao.ordem,
            acao=ligacao.acao,
            metodo_calculo=ligacao.metodo_calculo,
            regra_calculo=ligacao.regra_calculo,
            quantidade_base=ligacao.quantidade_base,
            rasgo_qt_comp=ligacao.rasgo_qt_comp,
            rasgo_qt_larg=ligacao.rasgo_qt_larg,
            tempo_setup_minutos=ligacao.tempo_setup_minutos,
            tempo_por_unidade_minutos=ligacao.tempo_por_unidade_minutos,
            unidade_tempo=ligacao.unidade_tempo,
            obrigatorio=ligacao.obrigatorio,
            ativo=ligacao.ativo,
            observacoes=ligacao.observacoes,
            created_at=ligacao.created_at,
            updated_at=ligacao.updated_at,
        )
