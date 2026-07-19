"""Service for piece operation link workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.metodo_calculo_types import normalize_metodo_calculo
from app.domain.regra_operacao_types import normalize_regra_operacao
from app.repositories.def_peca_operacao_repository import (
    DefPecaOperacaoRepository,
    DefPecaOperacaoResumo,
)


@dataclass(frozen=True)
class CriarDefPecaOperacaoData:
    """Input data for linking an operation to a piece definition."""

    def_peca_id: int | None
    def_operacao_id: int | None
    ordem: int = 1
    metodo_calculo: str | None = None
    regra_calculo: str | None = None
    quantidade_base: Decimal | None = None
    rasgo_qt_comp: int = 0
    rasgo_qt_larg: int = 0
    tempo_setup_minutos: Decimal | None = None
    tempo_por_unidade_minutos: Decimal | None = None
    unidade_tempo: str | None = None
    obrigatorio: bool = True
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarDefPecaOperacaoData:
    """Input data for editing a piece operation link."""

    def_peca_id: int | None
    def_operacao_id: int | None
    ordem: int = 1
    metodo_calculo: str | None = None
    regra_calculo: str | None = None
    quantidade_base: Decimal | None = None
    rasgo_qt_comp: int = 0
    rasgo_qt_larg: int = 0
    tempo_setup_minutos: Decimal | None = None
    tempo_por_unidade_minutos: Decimal | None = None
    unidade_tempo: str | None = None
    obrigatorio: bool = True
    ativo: bool = True
    observacoes: str | None = None


class DefPecaOperacaoService:
    """Application service for DefPecaOperacao workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefPecaOperacaoRepository(session)

    def listar_operacoes_da_peca(self, def_peca_id: int) -> list[DefPecaOperacaoResumo]:
        """List operations linked to one piece definition."""
        return self.repository.list_by_def_peca(def_peca_id)

    def listar_operacoes_ativas_da_peca(self, def_peca_id: int) -> list[DefPecaOperacaoResumo]:
        """List active operations linked to one piece definition."""
        return self.repository.list_active_by_def_peca(def_peca_id)

    def obter_por_id(self, id: int) -> DefPecaOperacaoResumo | None:
        """Get one piece operation link by id."""
        return self.repository.get_by_id(id)

    def adicionar_operacao_a_peca(
        self, data: CriarDefPecaOperacaoData
    ) -> DefPecaOperacaoResumo:
        """Link an operation to a piece definition."""
        def_peca_id = self._validate_required_id(data.def_peca_id, "def_peca_id")
        def_operacao_id = self._validate_required_id(data.def_operacao_id, "def_operacao_id")

        result = self.repository.create_peca_operacao(
            def_peca_id=def_peca_id,
            def_operacao_id=def_operacao_id,
            ordem=self._normalize_ordem(data.ordem),
            metodo_calculo=normalize_metodo_calculo(data.metodo_calculo),
            regra_calculo=self._normalize_regra_calculo(data.regra_calculo),
            quantidade_base=data.quantidade_base,
            rasgo_qt_comp=self._normalize_rasgo_qt(data.rasgo_qt_comp),
            rasgo_qt_larg=self._normalize_rasgo_qt(data.rasgo_qt_larg),
            tempo_setup_minutos=data.tempo_setup_minutos,
            tempo_por_unidade_minutos=data.tempo_por_unidade_minutos,
            unidade_tempo=self._normalize_unidade_tempo(data.unidade_tempo),
            obrigatorio=data.obrigatorio,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def editar_operacao_da_peca(
        self, id: int, data: EditarDefPecaOperacaoData
    ) -> DefPecaOperacaoResumo:
        """Edit one piece operation link."""
        def_peca_id = self._validate_required_id(data.def_peca_id, "def_peca_id")
        def_operacao_id = self._validate_required_id(data.def_operacao_id, "def_operacao_id")

        result = self.repository.update_peca_operacao(
            id=id,
            def_peca_id=def_peca_id,
            def_operacao_id=def_operacao_id,
            ordem=self._normalize_ordem(data.ordem),
            metodo_calculo=normalize_metodo_calculo(data.metodo_calculo),
            regra_calculo=self._normalize_regra_calculo(data.regra_calculo),
            quantidade_base=data.quantidade_base,
            rasgo_qt_comp=self._normalize_rasgo_qt(data.rasgo_qt_comp),
            rasgo_qt_larg=self._normalize_rasgo_qt(data.rasgo_qt_larg),
            tempo_setup_minutos=data.tempo_setup_minutos,
            tempo_por_unidade_minutos=data.tempo_por_unidade_minutos,
            unidade_tempo=self._normalize_unidade_tempo(data.unidade_tempo),
            obrigatorio=data.obrigatorio,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def desativar_operacao_da_peca(self, id: int) -> bool:
        """Deactivate one piece operation link."""
        deactivated = self.repository.deactivate_peca_operacao(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_operacao_da_peca(self, id: int) -> bool:
        """Reactivate one piece operation link."""
        activated = self.repository.activate_peca_operacao(id)
        if activated:
            self.session.commit()

        return activated

    def _validate_required_id(self, value: int | None, field_name: str) -> int:
        if not value:
            raise ValueError(f"{field_name} is required")

        return value

    def _normalize_ordem(self, ordem: int | None) -> int:
        if not ordem or ordem < 1:
            return 1

        return ordem

    def _normalize_rasgo_qt(self, value: int | None) -> int:
        value = int(value or 0)
        if value < 0 or value > 99:
            raise ValueError("quantidade de lados de rasgo deve estar entre 0 e 99")
        return value

    def _normalize_regra_calculo(self, regra_calculo: str | None) -> str | None:
        if regra_calculo is None or not regra_calculo.strip():
            return None

        return normalize_regra_operacao(regra_calculo)

    def _normalize_unidade_tempo(self, unidade_tempo: str | None) -> str | None:
        if unidade_tempo is None or not unidade_tempo.strip():
            return None

        return unidade_tempo.strip().upper()

# Note: the same operation MAY be linked several times to one piece — the new
# CNC model uses one link per calculation method (e.g. drilling + groove).
