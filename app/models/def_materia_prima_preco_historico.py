"""Price history of one raw material.

One row per price change, whatever brought it: the Excel import, someone
editing the material in the app, or a supplier answering a price request. It is
an append-only log — nothing here is ever rewritten, so the trail of what a
material cost, and when, stays honest.

Budgets do not read this table: each costing line already keeps its own copy of
the price it was calculated with. This is for looking back ("quanto subiu o
aglomerado este ano") and for the supplier cycle.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.materia_prima_types import ORIGEM_PRECO_MANUAL


class DefMateriaPrimaPrecoHistorico(Base):
    """One recorded price of a raw material."""

    __tablename__ = "def_materias_primas_precos_historico"
    __table_args__ = (
        Index(
            "ix_def_materias_primas_precos_historico_materia_prima_id",
            "materia_prima_id",
        ),
        Index("ix_def_materias_primas_precos_historico_ref_le", "ref_le"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    materia_prima_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # Copied so the history survives even if the material is later renumbered.
    ref_le: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preco_tabela: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    desconto: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    margem: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    preco_liquido: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    data_preco: Mapped[date | None] = mapped_column(Date, nullable=True)
    # EXCEL | MANUAL | FORNECEDOR (app.domain.materia_prima_types).
    origem: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=ORIGEM_PRECO_MANUAL,
        server_default=ORIGEM_PRECO_MANUAL,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])
