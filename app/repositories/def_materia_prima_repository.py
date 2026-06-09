"""Repository for internal raw material catalog reads and writes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import DefMateriaPrima


@dataclass(frozen=True)
class DefMateriaPrimaResumo:
    """Read model for listing internal raw materials."""

    id: int
    ref_le: str | None
    referencia_fornecedor: str | None
    descricao: str
    tipo_original_excel: str | None
    familia_original_excel: str | None
    tipo_martelo: str | None
    familia_martelo: str | None
    unidade: str | None
    preco_tabela: Decimal | None
    desconto: Decimal | None
    margem: Decimal | None
    preco_liquido: Decimal | None
    comprimento: Decimal | None
    largura: Decimal | None
    espessura: Decimal | None
    fornecedor: str | None
    origem_dados: str
    ativo: bool
    observacoes: str | None
    coresp_orla_0_4: str | None = None
    coresp_orla_1_0: str | None = None
    desperdicio_percentagem: Decimal | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DefMateriaPrimaRepository:
    """Repository for DefMateriaPrima operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[DefMateriaPrimaResumo]:
        """List all raw materials."""
        statement = select(DefMateriaPrima).order_by(
            DefMateriaPrima.descricao.asc(), DefMateriaPrima.id.asc()
        )
        materias = self.session.execute(statement).scalars().all()

        return [self._to_resumo(materia) for materia in materias]

    def list_active(self) -> list[DefMateriaPrimaResumo]:
        """List active raw materials."""
        statement = (
            select(DefMateriaPrima)
            .where(DefMateriaPrima.ativo.is_(True))
            .order_by(DefMateriaPrima.descricao.asc(), DefMateriaPrima.id.asc())
        )
        materias = self.session.execute(statement).scalars().all()

        return [self._to_resumo(materia) for materia in materias]

    def pesquisar(
        self, termo: str | None = None, limite: int = 200
    ) -> list[DefMateriaPrimaResumo]:
        """Search active raw materials by reference, description, type or family.

        An empty term lists the first ``limite`` active materials.
        """
        statement = select(DefMateriaPrima).where(DefMateriaPrima.ativo.is_(True))

        if termo and termo.strip():
            like = f"%{termo.strip()}%"
            statement = statement.where(
                or_(
                    DefMateriaPrima.ref_le.ilike(like),
                    DefMateriaPrima.descricao.ilike(like),
                    DefMateriaPrima.referencia_fornecedor.ilike(like),
                    DefMateriaPrima.tipo_martelo.ilike(like),
                    DefMateriaPrima.familia_martelo.ilike(like),
                )
            )

        statement = statement.order_by(
            DefMateriaPrima.descricao.asc(), DefMateriaPrima.id.asc()
        ).limit(limite)
        materias = self.session.execute(statement).scalars().all()

        return [self._to_resumo(materia) for materia in materias]

    def get_by_id(self, id: int) -> DefMateriaPrimaResumo | None:
        """Get one raw material by id."""
        materia = self.session.get(DefMateriaPrima, id)
        if materia is None:
            return None

        return self._to_resumo(materia)

    def get_by_ref_le(self, ref_le: str) -> DefMateriaPrimaResumo | None:
        """Get one raw material by its LE reference."""
        statement = select(DefMateriaPrima).where(DefMateriaPrima.ref_le == ref_le)
        materia = self.session.execute(statement).scalars().first()
        if materia is None:
            return None

        return self._to_resumo(materia)

    def create_materia_prima(
        self,
        *,
        descricao: str,
        ref_le: str | None = None,
        referencia_fornecedor: str | None = None,
        tipo_original_excel: str | None = None,
        familia_original_excel: str | None = None,
        tipo_martelo: str | None = None,
        familia_martelo: str | None = None,
        coresp_orla_0_4: str | None = None,
        coresp_orla_1_0: str | None = None,
        unidade: str | None = None,
        preco_tabela: Decimal | None = None,
        desconto: Decimal | None = None,
        margem: Decimal | None = None,
        desperdicio_percentagem: Decimal | None = None,
        preco_liquido: Decimal | None = None,
        comprimento: Decimal | None = None,
        largura: Decimal | None = None,
        espessura: Decimal | None = None,
        fornecedor: str | None = None,
        origem_dados: str = "EXCEL",
        ativo: bool = True,
        observacoes: str | None = None,
    ) -> DefMateriaPrimaResumo:
        """Create one raw material."""
        materia = DefMateriaPrima(
            descricao=descricao,
            ref_le=ref_le,
            referencia_fornecedor=referencia_fornecedor,
            tipo_original_excel=tipo_original_excel,
            familia_original_excel=familia_original_excel,
            tipo_martelo=tipo_martelo,
            familia_martelo=familia_martelo,
            coresp_orla_0_4=coresp_orla_0_4,
            coresp_orla_1_0=coresp_orla_1_0,
            unidade=unidade,
            preco_tabela=preco_tabela,
            desconto=desconto,
            margem=margem,
            desperdicio_percentagem=desperdicio_percentagem,
            preco_liquido=preco_liquido,
            comprimento=comprimento,
            largura=largura,
            espessura=espessura,
            fornecedor=fornecedor,
            origem_dados=origem_dados,
            ativo=ativo,
            observacoes=observacoes,
        )
        self.session.add(materia)
        self.session.flush()

        return self._to_resumo(materia)

    def update_materia_prima(
        self,
        *,
        id: int,
        descricao: str,
        ref_le: str | None = None,
        referencia_fornecedor: str | None = None,
        tipo_original_excel: str | None = None,
        familia_original_excel: str | None = None,
        tipo_martelo: str | None = None,
        familia_martelo: str | None = None,
        coresp_orla_0_4: str | None = None,
        coresp_orla_1_0: str | None = None,
        unidade: str | None = None,
        preco_tabela: Decimal | None = None,
        desconto: Decimal | None = None,
        margem: Decimal | None = None,
        desperdicio_percentagem: Decimal | None = None,
        preco_liquido: Decimal | None = None,
        comprimento: Decimal | None = None,
        largura: Decimal | None = None,
        espessura: Decimal | None = None,
        fornecedor: str | None = None,
        origem_dados: str = "EXCEL",
        ativo: bool = True,
        observacoes: str | None = None,
    ) -> DefMateriaPrimaResumo:
        """Update one raw material."""
        materia = self.session.get(DefMateriaPrima, id)
        if materia is None:
            raise ValueError("def_materia_prima not found")

        materia.descricao = descricao
        materia.ref_le = ref_le
        materia.referencia_fornecedor = referencia_fornecedor
        materia.tipo_original_excel = tipo_original_excel
        materia.familia_original_excel = familia_original_excel
        materia.tipo_martelo = tipo_martelo
        materia.familia_martelo = familia_martelo
        materia.coresp_orla_0_4 = coresp_orla_0_4
        materia.coresp_orla_1_0 = coresp_orla_1_0
        materia.unidade = unidade
        materia.preco_tabela = preco_tabela
        materia.desconto = desconto
        materia.margem = margem
        materia.desperdicio_percentagem = desperdicio_percentagem
        materia.preco_liquido = preco_liquido
        materia.comprimento = comprimento
        materia.largura = largura
        materia.espessura = espessura
        materia.fornecedor = fornecedor
        materia.origem_dados = origem_dados
        materia.ativo = ativo
        materia.observacoes = observacoes
        self.session.flush()

        return self._to_resumo(materia)

    def deactivate_materia_prima(self, id: int) -> bool:
        """Deactivate one raw material."""
        materia = self.session.get(DefMateriaPrima, id)
        if materia is None:
            return False

        materia.ativo = False
        self.session.flush()

        return True

    def _to_resumo(self, materia: DefMateriaPrima) -> DefMateriaPrimaResumo:
        """Convert an ORM raw material to the read model."""
        return DefMateriaPrimaResumo(
            id=materia.id,
            ref_le=materia.ref_le,
            referencia_fornecedor=materia.referencia_fornecedor,
            descricao=materia.descricao,
            tipo_original_excel=materia.tipo_original_excel,
            familia_original_excel=materia.familia_original_excel,
            tipo_martelo=materia.tipo_martelo,
            familia_martelo=materia.familia_martelo,
            coresp_orla_0_4=materia.coresp_orla_0_4,
            coresp_orla_1_0=materia.coresp_orla_1_0,
            desperdicio_percentagem=materia.desperdicio_percentagem,
            unidade=materia.unidade,
            preco_tabela=materia.preco_tabela,
            desconto=materia.desconto,
            margem=materia.margem,
            preco_liquido=materia.preco_liquido,
            comprimento=materia.comprimento,
            largura=materia.largura,
            espessura=materia.espessura,
            fornecedor=materia.fornecedor,
            origem_dados=materia.origem_dados,
            ativo=materia.ativo,
            observacoes=materia.observacoes,
            created_at=materia.created_at,
            updated_at=materia.updated_at,
        )
