"""Repository for the per-version board Não-Stock state (phase 8W.2)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.consumos import chave_placa
from app.domain.medidas import normalizar_numero
from app.models import OrcamentoVersaoPlacaNaoStock


@dataclass(frozen=True)
class PlacaNaoStockResumo:
    """Read model for one board Não-Stock row."""

    ref_le: str
    descricao: str
    esp: Decimal
    nao_stock: bool


class OrcamentoVersaoPlacaNaoStockRepository:
    """Repository for board Não-Stock operations."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_versao(self, orcamento_versao_id: int) -> list[PlacaNaoStockResumo]:
        """List the stored Não-Stock rows of a version."""
        statement = select(OrcamentoVersaoPlacaNaoStock).where(
            OrcamentoVersaoPlacaNaoStock.orcamento_versao_id == orcamento_versao_id
        )
        rows = self.session.execute(statement).scalars().all()
        return [
            PlacaNaoStockResumo(
                ref_le=row.ref_le,
                descricao=row.descricao,
                esp=row.esp,
                nao_stock=row.nao_stock,
            )
            for row in rows
        ]

    def chaves_ativas(self, orcamento_versao_id: int) -> set[tuple[str, str, str]]:
        """Return the normalized keys of the boards marked Não-Stock."""
        return {
            chave_placa(row.ref_le, row.descricao, row.esp)
            for row in self.list_by_versao(orcamento_versao_id)
            if row.nao_stock
        }

    def set_estado(
        self,
        orcamento_versao_id: int,
        ref_le,
        descricao,
        esp,
        nao_stock: bool,
    ) -> None:
        """Upsert the Não-Stock flag of one board (deletes the row when False)."""
        ref_le = (ref_le or "").strip()
        descricao = (descricao or "").strip()
        esp_val = normalizar_numero(esp) or Decimal("0")

        existente = self.session.execute(
            select(OrcamentoVersaoPlacaNaoStock).where(
                OrcamentoVersaoPlacaNaoStock.orcamento_versao_id == orcamento_versao_id,
                OrcamentoVersaoPlacaNaoStock.ref_le == ref_le,
                OrcamentoVersaoPlacaNaoStock.descricao == descricao,
                OrcamentoVersaoPlacaNaoStock.esp == esp_val,
            )
        ).scalars().first()

        if not nao_stock:
            if existente is not None:
                self.session.delete(existente)
            self.session.flush()
            return

        if existente is None:
            existente = OrcamentoVersaoPlacaNaoStock(
                orcamento_versao_id=orcamento_versao_id,
                ref_le=ref_le,
                descricao=descricao,
                esp=esp_val,
                nao_stock=True,
            )
            self.session.add(existente)
        else:
            existente.nao_stock = True
        self.session.flush()
