"""Service for budget item ValueSet line operation link workflows."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.regra_operacao_types import normalize_regra_operacao
from app.repositories.orcamento_item_valueset_linha_operacao_repository import (
    OrcamentoItemValuesetLinhaOperacaoRepository,
    OrcamentoItemValuesetLinhaOperacaoResumo,
)


@dataclass(frozen=True)
class CriarOrcamentoItemValuesetLinhaOperacaoData:
    """Input data for linking an operation to a budget item ValueSet line."""

    orcamento_item_valueset_linha_id: int | None
    def_operacao_id: int | None
    ordem: int = 1
    regra_calculo: str | None = None
    quantidade_base: Decimal | None = None
    tempo_setup_minutos: Decimal | None = None
    tempo_por_unidade_minutos: Decimal | None = None
    unidade_tempo: str | None = None
    obrigatorio: bool = True
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarOrcamentoItemValuesetLinhaOperacaoData:
    """Input data for editing a budget item ValueSet line operation link."""

    orcamento_item_valueset_linha_id: int | None
    def_operacao_id: int | None
    ordem: int = 1
    regra_calculo: str | None = None
    quantidade_base: Decimal | None = None
    tempo_setup_minutos: Decimal | None = None
    tempo_por_unidade_minutos: Decimal | None = None
    unidade_tempo: str | None = None
    obrigatorio: bool = True
    ativo: bool = True
    observacoes: str | None = None


class OrcamentoItemValuesetLinhaOperacaoService:
    """Application service for budget item ValueSet line operation links."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = OrcamentoItemValuesetLinhaOperacaoRepository(session)

    def listar_operacoes_da_linha(
        self, orcamento_item_valueset_linha_id: int
    ) -> list[OrcamentoItemValuesetLinhaOperacaoResumo]:
        """List operations linked to one budget item ValueSet line."""
        return self.repository.list_by_linha(orcamento_item_valueset_linha_id)

    def listar_operacoes_ativas_da_linha(
        self, orcamento_item_valueset_linha_id: int
    ) -> list[OrcamentoItemValuesetLinhaOperacaoResumo]:
        """List active operations linked to one budget item ValueSet line."""
        return self.repository.list_active_by_linha(orcamento_item_valueset_linha_id)

    def obter_por_id(self, id: int) -> OrcamentoItemValuesetLinhaOperacaoResumo | None:
        """Get one budget item ValueSet line operation link by id."""
        return self.repository.get_by_id(id)

    def adicionar_operacao_a_linha(
        self, data: CriarOrcamentoItemValuesetLinhaOperacaoData
    ) -> OrcamentoItemValuesetLinhaOperacaoResumo:
        """Link an operation to a budget item ValueSet line."""
        linha_id = self._validate_required_id(
            data.orcamento_item_valueset_linha_id, "orcamento_item_valueset_linha_id"
        )
        def_operacao_id = self._validate_required_id(data.def_operacao_id, "def_operacao_id")
        self._validate_nao_duplicada(linha_id, def_operacao_id, exclude_id=None)

        result = self.repository.create(
            orcamento_item_valueset_linha_id=linha_id,
            def_operacao_id=def_operacao_id,
            ordem=self._normalize_ordem(data.ordem),
            regra_calculo=self._normalize_regra_calculo(data.regra_calculo),
            quantidade_base=data.quantidade_base,
            tempo_setup_minutos=data.tempo_setup_minutos,
            tempo_por_unidade_minutos=data.tempo_por_unidade_minutos,
            unidade_tempo=self._normalize_unidade_tempo(data.unidade_tempo),
            obrigatorio=data.obrigatorio,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def editar_operacao_da_linha(
        self, id: int, data: EditarOrcamentoItemValuesetLinhaOperacaoData
    ) -> OrcamentoItemValuesetLinhaOperacaoResumo:
        """Edit one budget item ValueSet line operation link."""
        linha_id = self._validate_required_id(
            data.orcamento_item_valueset_linha_id, "orcamento_item_valueset_linha_id"
        )
        def_operacao_id = self._validate_required_id(data.def_operacao_id, "def_operacao_id")
        self._validate_nao_duplicada(linha_id, def_operacao_id, exclude_id=id)

        result = self.repository.update(
            id=id,
            orcamento_item_valueset_linha_id=linha_id,
            def_operacao_id=def_operacao_id,
            ordem=self._normalize_ordem(data.ordem),
            regra_calculo=self._normalize_regra_calculo(data.regra_calculo),
            quantidade_base=data.quantidade_base,
            tempo_setup_minutos=data.tempo_setup_minutos,
            tempo_por_unidade_minutos=data.tempo_por_unidade_minutos,
            unidade_tempo=self._normalize_unidade_tempo(data.unidade_tempo),
            obrigatorio=data.obrigatorio,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def desativar_operacao_da_linha(self, id: int) -> bool:
        """Deactivate one budget item ValueSet line operation link."""
        deactivated = self.repository.deactivate(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_operacao_da_linha(self, id: int) -> bool:
        """Reactivate one budget item ValueSet line operation link."""
        activated = self.repository.activate(id)
        if activated:
            self.session.commit()

        return activated

    def copiar_operacoes_de(
        self, origem_ops: Iterable, orcamento_item_valueset_linha_id: int
    ) -> int:
        """Replace the operations of one line with copies of the given operations.

        origem_ops can be any operation read model (model, budget or item level)
        sharing the def_operacao_id/ordem/regra_calculo/... shape. Does not
        commit: the caller controls the transaction boundary.
        """
        self.repository.delete_by_linha(orcamento_item_valueset_linha_id)

        total = 0
        for operacao in origem_ops:
            self.repository.create(
                orcamento_item_valueset_linha_id=orcamento_item_valueset_linha_id,
                def_operacao_id=operacao.def_operacao_id,
                ordem=operacao.ordem,
                regra_calculo=operacao.regra_calculo,
                quantidade_base=operacao.quantidade_base,
                tempo_setup_minutos=operacao.tempo_setup_minutos,
                tempo_por_unidade_minutos=operacao.tempo_por_unidade_minutos,
                unidade_tempo=operacao.unidade_tempo,
                obrigatorio=operacao.obrigatorio,
                ativo=operacao.ativo,
                observacoes=operacao.observacoes,
            )
            total += 1

        return total

    def _validate_required_id(self, value: int | None, field_name: str) -> int:
        if not value:
            raise ValueError(f"{field_name} is required")

        return value

    def _normalize_ordem(self, ordem: int | None) -> int:
        if not ordem or ordem < 1:
            return 1

        return ordem

    def _normalize_regra_calculo(self, regra_calculo: str | None) -> str | None:
        if regra_calculo is None or not regra_calculo.strip():
            return None

        return normalize_regra_operacao(regra_calculo)

    def _normalize_unidade_tempo(self, unidade_tempo: str | None) -> str | None:
        if unidade_tempo is None or not unidade_tempo.strip():
            return None

        return unidade_tempo.strip().upper()

    def _validate_nao_duplicada(
        self, orcamento_item_valueset_linha_id: int, def_operacao_id: int, exclude_id: int | None
    ) -> None:
        existentes = self.repository.list_by_linha(orcamento_item_valueset_linha_id)
        for existente in existentes:
            if existente.def_operacao_id == def_operacao_id and existente.id != exclude_id:
                raise ValueError("operacao ja associada a esta linha")
