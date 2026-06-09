"""Service for internal raw material catalog workflows."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.def_materia_prima import ORIGEM_DADOS_EXCEL
from app.repositories.def_materia_prima_repository import (
    DefMateriaPrimaRepository,
    DefMateriaPrimaResumo,
)


@dataclass(frozen=True)
class CriarDefMateriaPrimaData:
    """Input data for creating a raw material."""

    descricao: str
    ref_le: str | None = None
    referencia_fornecedor: str | None = None
    tipo_original_excel: str | None = None
    familia_original_excel: str | None = None
    tipo_martelo: str | None = None
    familia_martelo: str | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    unidade: str | None = None
    preco_tabela: Decimal | None = None
    desconto: Decimal | None = None
    margem: Decimal | None = None
    desperdicio_percentagem: Decimal | None = None
    preco_liquido: Decimal | None = None
    comprimento: Decimal | None = None
    largura: Decimal | None = None
    espessura: Decimal | None = None
    fornecedor: str | None = None
    origem_dados: str | None = None
    ativo: bool = True
    observacoes: str | None = None


@dataclass(frozen=True)
class EditarDefMateriaPrimaData:
    """Input data for editing a raw material."""

    descricao: str
    ref_le: str | None = None
    referencia_fornecedor: str | None = None
    tipo_original_excel: str | None = None
    familia_original_excel: str | None = None
    tipo_martelo: str | None = None
    familia_martelo: str | None = None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    unidade: str | None = None
    preco_tabela: Decimal | None = None
    desconto: Decimal | None = None
    margem: Decimal | None = None
    desperdicio_percentagem: Decimal | None = None
    preco_liquido: Decimal | None = None
    comprimento: Decimal | None = None
    largura: Decimal | None = None
    espessura: Decimal | None = None
    fornecedor: str | None = None
    origem_dados: str | None = None
    ativo: bool = True
    observacoes: str | None = None


class DefMateriaPrimaService:
    """Application service for DefMateriaPrima workflows."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = DefMateriaPrimaRepository(session)

    def listar_materias_primas(self) -> list[DefMateriaPrimaResumo]:
        """List all raw materials."""
        return self.repository.list_all()

    def listar_materias_primas_ativas(self) -> list[DefMateriaPrimaResumo]:
        """List active raw materials."""
        return self.repository.list_active()

    def pesquisar(
        self, termo: str | None = None, limite: int = 200
    ) -> list[DefMateriaPrimaResumo]:
        """Search active raw materials (an empty term lists the first results)."""
        return self.repository.pesquisar(termo, limite)

    def obter_por_id(self, id: int) -> DefMateriaPrimaResumo | None:
        """Get one raw material by id."""
        return self.repository.get_by_id(id)

    def obter_por_ref_le(self, ref_le: str | None) -> DefMateriaPrimaResumo | None:
        """Get one raw material by LE reference."""
        normalized = self._normalize_ref_le(ref_le)
        if normalized is None:
            return None

        return self.repository.get_by_ref_le(normalized)

    def criar_materia_prima(self, data: CriarDefMateriaPrimaData) -> DefMateriaPrimaResumo:
        """Create a raw material."""
        descricao = self._normalize_descricao(data.descricao)
        ref_le = self._normalize_ref_le(data.ref_le)
        origem_dados = self._normalize_origem_dados(data.origem_dados)
        self._validate_ref_le_unica(ref_le, exclude_id=None)

        result = self.repository.create_materia_prima(
            descricao=descricao,
            ref_le=ref_le,
            referencia_fornecedor=data.referencia_fornecedor,
            tipo_original_excel=data.tipo_original_excel,
            familia_original_excel=data.familia_original_excel,
            tipo_martelo=data.tipo_martelo,
            familia_martelo=data.familia_martelo,
            coresp_orla_0_4=data.coresp_orla_0_4,
            coresp_orla_1_0=data.coresp_orla_1_0,
            unidade=data.unidade,
            preco_tabela=data.preco_tabela,
            desconto=data.desconto,
            margem=data.margem,
            desperdicio_percentagem=data.desperdicio_percentagem,
            preco_liquido=data.preco_liquido,
            comprimento=data.comprimento,
            largura=data.largura,
            espessura=data.espessura,
            fornecedor=data.fornecedor,
            origem_dados=origem_dados,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def editar_materia_prima(
        self, id: int, data: EditarDefMateriaPrimaData
    ) -> DefMateriaPrimaResumo:
        """Edit a raw material."""
        descricao = self._normalize_descricao(data.descricao)
        ref_le = self._normalize_ref_le(data.ref_le)
        origem_dados = self._normalize_origem_dados(data.origem_dados)
        self._validate_ref_le_unica(ref_le, exclude_id=id)

        result = self.repository.update_materia_prima(
            id=id,
            descricao=descricao,
            ref_le=ref_le,
            referencia_fornecedor=data.referencia_fornecedor,
            tipo_original_excel=data.tipo_original_excel,
            familia_original_excel=data.familia_original_excel,
            tipo_martelo=data.tipo_martelo,
            familia_martelo=data.familia_martelo,
            coresp_orla_0_4=data.coresp_orla_0_4,
            coresp_orla_1_0=data.coresp_orla_1_0,
            unidade=data.unidade,
            preco_tabela=data.preco_tabela,
            desconto=data.desconto,
            margem=data.margem,
            desperdicio_percentagem=data.desperdicio_percentagem,
            preco_liquido=data.preco_liquido,
            comprimento=data.comprimento,
            largura=data.largura,
            espessura=data.espessura,
            fornecedor=data.fornecedor,
            origem_dados=origem_dados,
            ativo=data.ativo,
            observacoes=data.observacoes,
        )
        self.session.commit()

        return result

    def desativar_materia_prima(self, id: int) -> bool:
        """Deactivate a raw material."""
        deactivated = self.repository.deactivate_materia_prima(id)
        if deactivated:
            self.session.commit()

        return deactivated

    def _normalize_descricao(self, descricao: str | None) -> str:
        normalized = (descricao or "").strip()
        if not normalized:
            raise ValueError("descricao is required")

        return normalized

    def _normalize_ref_le(self, ref_le: str | None) -> str | None:
        if ref_le is None:
            return None

        normalized = ref_le.strip()
        return normalized or None

    def _normalize_origem_dados(self, origem_dados: str | None) -> str:
        if not origem_dados or not origem_dados.strip():
            return ORIGEM_DADOS_EXCEL

        return origem_dados.strip()

    def _validate_ref_le_unica(self, ref_le: str | None, exclude_id: int | None) -> None:
        if ref_le is None:
            return

        existing = self.repository.get_by_ref_le(ref_le)
        if existing is not None and existing.id != exclude_id:
            raise ValueError("ref_le ja existe")
