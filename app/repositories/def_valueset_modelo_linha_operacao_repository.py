"""Repository for ValueSet model line operation link reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefValuesetModeloLinhaOperacao


@dataclass(frozen=True)
class DefValuesetModeloLinhaOperacaoResumo:
    """Read model for operations associated with a reusable ValueSet model line."""

    id: int
    def_valueset_modelo_linha_id: int
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
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefValuesetModeloLinhaOperacaoRepository:
    """Repository for DefValuesetModeloLinhaOperacao operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_linha(
        self, def_valueset_modelo_linha_id: int
    ) -> list[DefValuesetModeloLinhaOperacaoResumo]:
        """List operations linked to one ValueSet model line."""
        statement = (
            select(DefValuesetModeloLinhaOperacao)
            .where(
                DefValuesetModeloLinhaOperacao.def_valueset_modelo_linha_id
                == def_valueset_modelo_linha_id
            )
            .order_by(
                DefValuesetModeloLinhaOperacao.ordem.asc(),
                DefValuesetModeloLinhaOperacao.id.asc(),
            )
        )
        ligacoes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(ligacao) for ligacao in ligacoes]

    def list_active_by_linha(
        self, def_valueset_modelo_linha_id: int
    ) -> list[DefValuesetModeloLinhaOperacaoResumo]:
        """List active operations linked to one ValueSet model line."""
        statement = (
            select(DefValuesetModeloLinhaOperacao)
            .where(
                DefValuesetModeloLinhaOperacao.def_valueset_modelo_linha_id
                == def_valueset_modelo_linha_id,
                DefValuesetModeloLinhaOperacao.ativo.is_(True),
            )
            .order_by(
                DefValuesetModeloLinhaOperacao.ordem.asc(),
                DefValuesetModeloLinhaOperacao.id.asc(),
            )
        )
        ligacoes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(ligacao) for ligacao in ligacoes]

    def get_by_id(self, id: int) -> DefValuesetModeloLinhaOperacaoResumo | None:
        """Get one ValueSet model line operation link by id."""
        ligacao = self.session.get(DefValuesetModeloLinhaOperacao, id)
        if ligacao is None:
            return None

        return self._to_resumo(ligacao)

    def create(
        self,
        *,
        def_valueset_modelo_linha_id: int,
        def_operacao_id: int,
        ordem: int = 1,
        acao: str = "ADICIONAR",
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
    ) -> DefValuesetModeloLinhaOperacaoResumo:
        """Create one ValueSet model line operation link."""
        ligacao = DefValuesetModeloLinhaOperacao(
            def_valueset_modelo_linha_id=def_valueset_modelo_linha_id,
            def_operacao_id=def_operacao_id,
            ordem=ordem,
            acao=acao,
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
        def_valueset_modelo_linha_id: int,
        def_operacao_id: int,
        ordem: int = 1,
        acao: str = "ADICIONAR",
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
    ) -> DefValuesetModeloLinhaOperacaoResumo:
        """Update one ValueSet model line operation link."""
        ligacao = self.session.get(DefValuesetModeloLinhaOperacao, id)
        if ligacao is None:
            raise ValueError("def_valueset_modelo_linha_operacao not found")

        ligacao.def_valueset_modelo_linha_id = def_valueset_modelo_linha_id
        ligacao.def_operacao_id = def_operacao_id
        ligacao.ordem = ordem
        ligacao.acao = acao
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
        """Deactivate one ValueSet model line operation link."""
        ligacao = self.session.get(DefValuesetModeloLinhaOperacao, id)
        if ligacao is None:
            return False

        ligacao.ativo = False
        self.session.flush()

        return True

    def activate(self, id: int) -> bool:
        """Reactivate one ValueSet model line operation link."""
        ligacao = self.session.get(DefValuesetModeloLinhaOperacao, id)
        if ligacao is None:
            return False

        ligacao.ativo = True
        self.session.flush()

        return True

    def _to_resumo(
        self, ligacao: DefValuesetModeloLinhaOperacao
    ) -> DefValuesetModeloLinhaOperacaoResumo:
        """Convert an ORM ValueSet model line operation link to read model."""
        return DefValuesetModeloLinhaOperacaoResumo(
            id=ligacao.id,
            def_valueset_modelo_linha_id=ligacao.def_valueset_modelo_linha_id,
            def_operacao_id=ligacao.def_operacao_id,
            ordem=ligacao.ordem,
            acao=ligacao.acao,
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
