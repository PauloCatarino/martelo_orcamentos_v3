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
    suplemento_ativo: bool = False
    suplemento_ref_le: str | None = None
    suplemento_valor_base: Decimal | None = None
    suplemento_valor_local: Decimal | None = None
    suplemento_editado_localmente: bool = False
    suplemento_nota_cliente: str | None = None
    suplemento_quantidade: Decimal = Decimal("1")


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
                suplemento_ativo=row.suplemento_ativo,
                suplemento_ref_le=row.suplemento_ref_le,
                suplemento_valor_base=row.suplemento_valor_base,
                suplemento_valor_local=row.suplemento_valor_local,
                suplemento_editado_localmente=row.suplemento_editado_localmente,
                suplemento_nota_cliente=row.suplemento_nota_cliente,
                suplemento_quantidade=row.suplemento_quantidade or Decimal("1"),
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
        """Upsert the Não-Stock flag of one board.

        A row with an active supplement is retained when the whole-board flag
        is disabled because both settings share the same per-version key.
        """
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
                if existente.suplemento_ativo:
                    existente.nao_stock = False
                else:
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

    def set_suplemento(
        self,
        orcamento_versao_id: int,
        ref_le,
        descricao,
        esp,
        *,
        ativo: bool,
        suplemento_ref_le: str | None = None,
        valor_base: Decimal | None = None,
        valor_local: Decimal | None = None,
        editado_localmente: bool = False,
        nota_cliente: str | None = None,
        quantidade: Decimal = Decimal("1"),
    ) -> None:
        """Upsert a once-per-reference material supplement for the version."""
        ref_le = (ref_le or "").strip()
        descricao = (descricao or "").strip()
        esp_val = normalizar_numero(esp) or Decimal("0")
        existente = self._get_row(orcamento_versao_id, ref_le, descricao, esp_val)
        mesma_referencia = self.session.execute(
            select(OrcamentoVersaoPlacaNaoStock).where(
                OrcamentoVersaoPlacaNaoStock.orcamento_versao_id
                == orcamento_versao_id,
                OrcamentoVersaoPlacaNaoStock.ref_le == ref_le,
            )
        ).scalars().all()

        if not ativo:
            for row in mesma_referencia:
                row.suplemento_ativo = False
            if existente is None:
                self.session.flush()
                return

        if existente is None:
            existente = OrcamentoVersaoPlacaNaoStock(
                orcamento_versao_id=orcamento_versao_id,
                ref_le=ref_le,
                descricao=descricao,
                esp=esp_val,
                nao_stock=False,
            )
            self.session.add(existente)

        if ativo:
            for row in mesma_referencia:
                if row is not existente:
                    row.suplemento_ativo = False

        existente.suplemento_ativo = bool(ativo)
        existente.suplemento_ref_le = (
            (suplemento_ref_le or "").strip() or None
        )
        existente.suplemento_valor_base = valor_base
        existente.suplemento_valor_local = valor_local
        existente.suplemento_editado_localmente = bool(editado_localmente)
        existente.suplemento_nota_cliente = (nota_cliente or "").strip() or None
        existente.suplemento_quantidade = quantidade
        self.session.flush()

    def _get_row(
        self,
        orcamento_versao_id: int,
        ref_le: str,
        descricao: str,
        esp: Decimal,
    ) -> OrcamentoVersaoPlacaNaoStock | None:
        return self.session.execute(
            select(OrcamentoVersaoPlacaNaoStock).where(
                OrcamentoVersaoPlacaNaoStock.orcamento_versao_id == orcamento_versao_id,
                OrcamentoVersaoPlacaNaoStock.ref_le == ref_le,
                OrcamentoVersaoPlacaNaoStock.descricao == descricao,
                OrcamentoVersaoPlacaNaoStock.esp == esp,
            )
        ).scalars().first()
