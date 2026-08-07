"""Service for ValueSet model line operation link workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.metodo_calculo_types import normalize_metodo_calculo
from app.domain.regra_operacao_types import normalize_regra_operacao
from app.domain.operacao_acao_types import normalize_operacao_acao
from app.repositories.def_valueset_modelo_linha_operacao_repository import (
    DefValuesetModeloLinhaOperacaoRepository,
    DefValuesetModeloLinhaOperacaoResumo,
)


@dataclass(frozen=True)
class CriarDefValuesetModeloLinhaOperacaoData:
    """Input data for linking an operation to a ValueSet model line."""

    def_valueset_modelo_linha_id: int | None
    def_operacao_id: int | None
    ordem: int = 1
    acao: str | None = None
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
class EditarDefValuesetModeloLinhaOperacaoData:
    """Input data for editing a ValueSet model line operation link."""

    def_valueset_modelo_linha_id: int | None
    def_operacao_id: int | None
    ordem: int = 1
    acao: str | None = None
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


class DefValuesetModeloLinhaOperacaoService:
    """Application service for ValueSet model line operation links."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefValuesetModeloLinhaOperacaoRepository(session)

    def listar_operacoes_da_linha(
        self, def_valueset_modelo_linha_id: int
    ) -> list[DefValuesetModeloLinhaOperacaoResumo]:
        """List operations linked to one ValueSet model line."""
        return self.repository.list_by_linha(def_valueset_modelo_linha_id)

    def listar_operacoes_ativas_da_linha(
        self, def_valueset_modelo_linha_id: int
    ) -> list[DefValuesetModeloLinhaOperacaoResumo]:
        """List active operations linked to one ValueSet model line."""
        return self.repository.list_active_by_linha(def_valueset_modelo_linha_id)

    def obter_por_id(self, id: int) -> DefValuesetModeloLinhaOperacaoResumo | None:
        """Get one ValueSet model line operation link by id."""
        return self.repository.get_by_id(id)

    def adicionar_operacao_a_linha(
        self, data: CriarDefValuesetModeloLinhaOperacaoData
    ) -> DefValuesetModeloLinhaOperacaoResumo:
        """Link an operation to a ValueSet model line."""
        linha_id = self._validate_required_id(
            data.def_valueset_modelo_linha_id, "def_valueset_modelo_linha_id"
        )
        def_operacao_id = self._validate_required_id(data.def_operacao_id, "def_operacao_id")

        result = self.repository.create(
            def_valueset_modelo_linha_id=linha_id,
            def_operacao_id=def_operacao_id,
            ordem=self._normalize_ordem(data.ordem),
            acao=normalize_operacao_acao(data.acao),
            metodo_calculo=normalize_metodo_calculo(data.metodo_calculo),
            regra_calculo=self._normalize_regra_calculo(data.regra_calculo),
            quantidade_base=data.quantidade_base,
            rasgo_qt_comp=data.rasgo_qt_comp,
            rasgo_qt_larg=data.rasgo_qt_larg,
            tempo_setup_minutos=data.tempo_setup_minutos,
            tempo_por_unidade_minutos=data.tempo_por_unidade_minutos,
            unidade_tempo=self._normalize_unidade_tempo(data.unidade_tempo),
            obrigatorio=data.obrigatorio,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def copiar_operacoes_entre_linhas(self, origem_id: int, destino_id: int) -> int:
        """Copy every operation of one line onto another. Returns how many.

        Used by "Gravar como…": a variant copied from another one has to bring
        its operations, senão a linha nova custeia diferente da original sem o
        utilizador dar por isso. Inactive links are copied as they are.
        """
        copiadas = 0
        for ligacao in self.repository.list_by_linha(origem_id):
            self.repository.create(
                def_valueset_modelo_linha_id=destino_id,
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
            )
            copiadas += 1

        if copiadas:
            self.session.commit()

        return copiadas

    def substituir_operacoes_de(
        self,
        origem: list[DefValuesetModeloLinhaOperacaoResumo],
        destino_id: int,
        *,
        commit: bool = True,
    ) -> int:
        """Make destination operations equal to a detached source snapshot.

        Existing destination links are reused in display order, missing links
        are created and surplus links are only deactivated. This preserves
        audit history, avoids destructive deletes and makes repeated pastes
        idempotent.
        """
        existentes = self.repository.list_by_linha(destino_id)

        for indice, ligacao in enumerate(origem):
            fields = self._copy_fields(ligacao, destino_id)
            if indice < len(existentes):
                self.repository.update(id=existentes[indice].id, **fields)
            else:
                self.repository.create(**fields)

        for excedente in existentes[len(origem) :]:
            self.repository.deactivate(excedente.id)

        if commit:
            self.session.commit()

        return len(origem)

    def editar_operacao_da_linha(
        self, id: int, data: EditarDefValuesetModeloLinhaOperacaoData
    ) -> DefValuesetModeloLinhaOperacaoResumo:
        """Edit one ValueSet model line operation link."""
        linha_id = self._validate_required_id(
            data.def_valueset_modelo_linha_id, "def_valueset_modelo_linha_id"
        )
        def_operacao_id = self._validate_required_id(data.def_operacao_id, "def_operacao_id")

        result = self.repository.update(
            id=id,
            def_valueset_modelo_linha_id=linha_id,
            def_operacao_id=def_operacao_id,
            ordem=self._normalize_ordem(data.ordem),
            acao=normalize_operacao_acao(data.acao),
            metodo_calculo=normalize_metodo_calculo(data.metodo_calculo),
            regra_calculo=self._normalize_regra_calculo(data.regra_calculo),
            quantidade_base=data.quantidade_base,
            rasgo_qt_comp=data.rasgo_qt_comp,
            rasgo_qt_larg=data.rasgo_qt_larg,
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
        """Deactivate one ValueSet model line operation link."""
        deactivated = self.repository.deactivate(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_operacao_da_linha(self, id: int) -> bool:
        """Reactivate one ValueSet model line operation link."""
        activated = self.repository.activate(id)
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

    def _normalize_regra_calculo(self, regra_calculo: str | None) -> str | None:
        if regra_calculo is None or not regra_calculo.strip():
            return None

        return normalize_regra_operacao(regra_calculo)

    def _normalize_unidade_tempo(self, unidade_tempo: str | None) -> str | None:
        if unidade_tempo is None or not unidade_tempo.strip():
            return None

        return unidade_tempo.strip().upper()

    @staticmethod
    def _copy_fields(
        ligacao: DefValuesetModeloLinhaOperacaoResumo, destino_id: int
    ) -> dict:
        """Build operation fields without copying link identity or timestamps."""
        return {
            "def_valueset_modelo_linha_id": destino_id,
            "def_operacao_id": ligacao.def_operacao_id,
            "ordem": ligacao.ordem,
            "acao": ligacao.acao,
            "metodo_calculo": ligacao.metodo_calculo,
            "regra_calculo": ligacao.regra_calculo,
            "quantidade_base": ligacao.quantidade_base,
            "rasgo_qt_comp": ligacao.rasgo_qt_comp,
            "rasgo_qt_larg": ligacao.rasgo_qt_larg,
            "tempo_setup_minutos": ligacao.tempo_setup_minutos,
            "tempo_por_unidade_minutos": ligacao.tempo_por_unidade_minutos,
            "unidade_tempo": ligacao.unidade_tempo,
            "obrigatorio": ligacao.obrigatorio,
            "ativo": ligacao.ativo,
            "observacoes": ligacao.observacoes,
        }

