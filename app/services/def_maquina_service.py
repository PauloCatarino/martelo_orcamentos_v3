"""Service for machine catalog workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.repositories.def_maquina_repository import DefMaquinaRepository, DefMaquinaResumo


@dataclass(frozen=True)
class CriarDefMaquinaData:
    """Input data for creating a machine."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    custo_hora: Decimal | None = None
    custo_hora_serie: Decimal | None = None
    preco_ml_std: Decimal | None = None
    preco_ml_serie: Decimal | None = None
    permite_rasgos: bool = False
    preco_rasgo_ml_std: Decimal | None = None
    preco_rasgo_ml_serie: Decimal | None = None
    preco_lado_curto_std: Decimal | None = None
    preco_lado_curto_serie: Decimal | None = None
    preco_lado_longo_std: Decimal | None = None
    preco_lado_longo_serie: Decimal | None = None
    limite_lado_mm: Decimal | None = None
    custo_setup_peca_std: Decimal | None = None
    custo_setup_peca_serie: Decimal | None = None
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarDefMaquinaData:
    """Input data for editing a machine."""

    codigo: str
    nome: str
    descricao: str | None = None
    tipo: str | None = None
    custo_hora: Decimal | None = None
    custo_hora_serie: Decimal | None = None
    preco_ml_std: Decimal | None = None
    preco_ml_serie: Decimal | None = None
    permite_rasgos: bool = False
    preco_rasgo_ml_std: Decimal | None = None
    preco_rasgo_ml_serie: Decimal | None = None
    preco_lado_curto_std: Decimal | None = None
    preco_lado_curto_serie: Decimal | None = None
    preco_lado_longo_std: Decimal | None = None
    preco_lado_longo_serie: Decimal | None = None
    limite_lado_mm: Decimal | None = None
    custo_setup_peca_std: Decimal | None = None
    custo_setup_peca_serie: Decimal | None = None
    ativo: bool = True
    observacoes: str | None = None


class DefMaquinaService:
    """Application service for DefMaquina workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefMaquinaRepository(session)

    def listar_maquinas(self) -> list[DefMaquinaResumo]:
        """List all machines."""
        return self.repository.list_all()

    def listar_maquinas_ativas(self) -> list[DefMaquinaResumo]:
        """List active machines."""
        return self.repository.list_active()

    def obter_por_id(self, id: int) -> DefMaquinaResumo | None:
        """Get one machine by id."""
        return self.repository.get_by_id(id)

    def obter_por_codigo(self, codigo: str | None) -> DefMaquinaResumo | None:
        """Get one machine by code."""
        normalized = self._normalize_codigo(codigo, required=False)
        if normalized is None:
            return None

        return self.repository.get_by_codigo(normalized)

    def criar_maquina(self, data: CriarDefMaquinaData) -> DefMaquinaResumo:
        """Create a machine."""
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")
        self._validate_codigo_unico(codigo, exclude_id=None)

        result = self.repository.create_maquina(
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            tipo=self._normalize_optional_text(data.tipo),
            custo_hora=data.custo_hora,
            custo_hora_serie=data.custo_hora_serie,
            preco_ml_std=data.preco_ml_std,
            preco_ml_serie=data.preco_ml_serie,
            permite_rasgos=data.permite_rasgos,
            preco_rasgo_ml_std=data.preco_rasgo_ml_std,
            preco_rasgo_ml_serie=data.preco_rasgo_ml_serie,
            preco_lado_curto_std=data.preco_lado_curto_std,
            preco_lado_curto_serie=data.preco_lado_curto_serie,
            preco_lado_longo_std=data.preco_lado_longo_std,
            preco_lado_longo_serie=data.preco_lado_longo_serie,
            limite_lado_mm=data.limite_lado_mm,
            custo_setup_peca_std=data.custo_setup_peca_std,
            custo_setup_peca_serie=data.custo_setup_peca_serie,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def editar_maquina(self, id: int, data: EditarDefMaquinaData) -> DefMaquinaResumo:
        """Edit a machine."""
        codigo = self._normalize_codigo(data.codigo)
        nome = self._normalize_required_text(data.nome, "nome")
        self._validate_codigo_unico(codigo, exclude_id=id)

        result = self.repository.update_maquina(
            id=id,
            codigo=codigo,
            nome=nome,
            descricao=data.descricao,
            tipo=self._normalize_optional_text(data.tipo),
            custo_hora=data.custo_hora,
            custo_hora_serie=data.custo_hora_serie,
            preco_ml_std=data.preco_ml_std,
            preco_ml_serie=data.preco_ml_serie,
            permite_rasgos=data.permite_rasgos,
            preco_rasgo_ml_std=data.preco_rasgo_ml_std,
            preco_rasgo_ml_serie=data.preco_rasgo_ml_serie,
            preco_lado_curto_std=data.preco_lado_curto_std,
            preco_lado_curto_serie=data.preco_lado_curto_serie,
            preco_lado_longo_std=data.preco_lado_longo_std,
            preco_lado_longo_serie=data.preco_lado_longo_serie,
            limite_lado_mm=data.limite_lado_mm,
            custo_setup_peca_std=data.custo_setup_peca_std,
            custo_setup_peca_serie=data.custo_setup_peca_serie,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def desativar_maquina(self, id: int) -> bool:
        """Deactivate a machine."""
        deactivated = self.repository.deactivate_maquina(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def ativar_maquina(self, id: int) -> bool:
        """Reactivate a machine."""
        activated = self.repository.activate_maquina(id)
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

    def _validate_codigo_unico(self, codigo: str, exclude_id: int | None) -> None:
        existing = self.repository.get_by_codigo(codigo)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("codigo ja existe")
