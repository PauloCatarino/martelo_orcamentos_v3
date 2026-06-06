"""Service for operation catalog workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.domain.operacao_types import normalize_operacao_type
from app.repositories.def_operacao_repository import DefOperacaoRepository, DefOperacaoResumo


@dataclass(frozen=True)
class CriarDefOperacaoData:
    """Input data for creating an operation."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo_operacao: str | None = None
    unidade_calculo: str | None = None
    tempo_base: Decimal | None = None
    tempo_setup: Decimal | None = None
    custo_hora: Decimal | None = None
    custo_minimo: Decimal | None = None
    maquina_id: int | None = None
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarDefOperacaoData:
    """Input data for editing an operation."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo_operacao: str | None = None
    unidade_calculo: str | None = None
    tempo_base: Decimal | None = None
    tempo_setup: Decimal | None = None
    custo_hora: Decimal | None = None
    custo_minimo: Decimal | None = None
    maquina_id: int | None = None
    ativo: bool = True
    observacoes: str | None = None


class DefOperacaoService:
    """Application service for DefOperacao workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefOperacaoRepository(session)

    def listar_operacoes(self) -> list[DefOperacaoResumo]:
        """List all operations."""
        return self.repository.list_all()

    def listar_operacoes_ativas(self) -> list[DefOperacaoResumo]:
        """List active operations."""
        return self.repository.list_active()

    def obter_por_id(self, id: int) -> DefOperacaoResumo | None:
        """Get one operation by id."""
        return self.repository.get_by_id(id)

    def obter_por_codigo(self, codigo: str | None) -> DefOperacaoResumo | None:
        """Get one operation by code."""
        normalized = self._normalize_codigo(codigo, required=False)
        if normalized is None:
            return None

        return self.repository.get_by_codigo(normalized)

    def criar_operacao(self, data: CriarDefOperacaoData) -> DefOperacaoResumo:
        """Create an operation."""
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")
        self._validate_codigo_unico(codigo, exclude_id=None)

        result = self.repository.create_operacao(
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            tipo_operacao=self._normalize_tipo_operacao(data.tipo_operacao),
            unidade_calculo=self._normalize_optional_text(data.unidade_calculo),
            tempo_base=data.tempo_base,
            tempo_setup=data.tempo_setup,
            custo_hora=data.custo_hora,
            custo_minimo=data.custo_minimo,
            maquina_id=data.maquina_id,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def editar_operacao(self, id: int, data: EditarDefOperacaoData) -> DefOperacaoResumo:
        """Edit an operation."""
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")
        self._validate_codigo_unico(codigo, exclude_id=id)

        result = self.repository.update_operacao(
            id=id,
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            tipo_operacao=self._normalize_tipo_operacao(data.tipo_operacao),
            unidade_calculo=self._normalize_optional_text(data.unidade_calculo),
            tempo_base=data.tempo_base,
            tempo_setup=data.tempo_setup,
            custo_hora=data.custo_hora,
            custo_minimo=data.custo_minimo,
            maquina_id=data.maquina_id,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def desativar_operacao(self, id: int) -> bool:
        """Deactivate an operation."""
        deactivated = self.repository.deactivate_operacao(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_operacao(self, id: int) -> bool:
        """Reactivate an operation."""
        activated = self.repository.activate_operacao(id)
        if activated:
            self.session.commit()

        return activated

    def _normalize_codigo(self, codigo: str | None, required: bool = True) -> str | None:
        normalized = (codigo or "").strip().upper()
        if not normalized and required:
            raise ValueError("codigo is required")

        return normalized or None

    def _normalize_required_text(self, value: str | None, field_name: str) -> str:
        normalized = (value or "").strip()
        if not normalized:
            raise ValueError(f"{field_name} is required")

        return normalized

    def _normalize_optional_text(self, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    def _normalize_tipo_operacao(self, tipo_operacao: str | None) -> str | None:
        if tipo_operacao is None or not tipo_operacao.strip():
            return None

        return normalize_operacao_type(tipo_operacao)

    def _validate_codigo_unico(self, codigo: str, exclude_id: int | None) -> None:
        existing = self.repository.get_by_codigo(codigo)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("codigo ja existe")
