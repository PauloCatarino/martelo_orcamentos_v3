"""Repository for piece operation link reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DefPecaOperacao


@dataclass(frozen=True)
class DefPecaOperacaoResumo:
    """Read model for operations associated with a piece definition."""

    id: int
    def_peca_id: int
    def_operacao_id: int
    ordem: int
    regra_calculo: str | None
    quantidade_base: Decimal | None
    obrigatorio: bool
    ativo: bool
    observacoes: str | None
    rasgo_qt_comp: int = 0
    rasgo_qt_larg: int = 0
    tempo_setup_minutos: Decimal | None = None
    tempo_por_unidade_minutos: Decimal | None = None
    unidade_tempo: str | None = None
    metodo_calculo: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefPecaOperacaoRepository:
    """Repository for DefPecaOperacao operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_def_peca(self, def_peca_id: int) -> list[DefPecaOperacaoResumo]:
        """List operations linked to one piece definition."""
        statement = (
            select(DefPecaOperacao)
            .where(DefPecaOperacao.def_peca_id == def_peca_id)
            .order_by(DefPecaOperacao.ordem.asc(), DefPecaOperacao.id.asc())
        )
        ligacoes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(ligacao) for ligacao in ligacoes]

    def list_active_by_def_peca(self, def_peca_id: int) -> list[DefPecaOperacaoResumo]:
        """List active operations linked to one piece definition."""
        statement = (
            select(DefPecaOperacao)
            .where(
                DefPecaOperacao.def_peca_id == def_peca_id,
                DefPecaOperacao.ativo.is_(True),
            )
            .order_by(DefPecaOperacao.ordem.asc(), DefPecaOperacao.id.asc())
        )
        ligacoes = self.session.execute(statement).scalars().all()

        return [self._to_resumo(ligacao) for ligacao in ligacoes]

    def get_by_id(self, id: int) -> DefPecaOperacaoResumo | None:
        """Get one piece operation link by id."""
        ligacao = self.session.get(DefPecaOperacao, id)
        if ligacao is None:
            return None

        return self._to_resumo(ligacao)

    def create_peca_operacao(
        self,
        *,
        def_peca_id: int,
        def_operacao_id: int,
        ordem: int = 1,
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
    ) -> DefPecaOperacaoResumo:
        """Create one piece operation link."""
        ligacao = DefPecaOperacao(
            def_peca_id=def_peca_id,
            def_operacao_id=def_operacao_id,
            ordem=ordem,
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

    def update_peca_operacao(
        self,
        *,
        id: int,
        def_peca_id: int,
        def_operacao_id: int,
        ordem: int = 1,
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
    ) -> DefPecaOperacaoResumo:
        """Update one piece operation link."""
        ligacao = self.session.get(DefPecaOperacao, id)
        if ligacao is None:
            raise ValueError("def_peca_operacao not found")

        ligacao.def_peca_id = def_peca_id
        ligacao.def_operacao_id = def_operacao_id
        ligacao.ordem = ordem
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

    def deactivate_peca_operacao(self, id: int) -> bool:
        """Deactivate one piece operation link."""
        ligacao = self.session.get(DefPecaOperacao, id)
        if ligacao is None:
            return False

        ligacao.ativo = False
        self.session.flush()

        return True

    def activate_peca_operacao(self, id: int) -> bool:
        """Reactivate one piece operation link."""
        ligacao = self.session.get(DefPecaOperacao, id)
        if ligacao is None:
            return False

        ligacao.ativo = True
        self.session.flush()

        return True

    def _to_resumo(self, ligacao: DefPecaOperacao) -> DefPecaOperacaoResumo:
        """Convert an ORM piece operation link to the read model."""
        return DefPecaOperacaoResumo(
            id=ligacao.id,
            def_peca_id=ligacao.def_peca_id,
            def_operacao_id=ligacao.def_operacao_id,
            ordem=ligacao.ordem,
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
