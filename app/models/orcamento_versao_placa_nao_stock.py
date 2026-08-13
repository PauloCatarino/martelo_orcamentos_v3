"""Per-version state of boards that need special non-stock treatment.

A board ("placa") of a budget version is identified by (ref_le, descricao,
esp). When marked Não-Stock, the budget uses the WHOLE-BOARD cost (C.Placa Usad)
for that board instead of the %-waste cost. The state lives in this table so it
survives any costing recompute and line recreation.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrcamentoVersaoPlacaNaoStock(Base):
    """Não-Stock flag for one board of a budget version."""

    __tablename__ = "orcamento_versao_placa_nao_stock"
    __table_args__ = (
        UniqueConstraint(
            "orcamento_versao_id",
            "ref_le",
            "descricao",
            "esp",
            name="uq_versao_placa_nao_stock",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_versao_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_versoes.id"),
        nullable=False,
        index=True,
    )
    ref_le: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    descricao: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    esp: Mapped[Decimal] = mapped_column(
        Numeric(12, 4), nullable=False, default=Decimal("0")
    )
    nao_stock: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    suplemento_ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    suplemento_ref_le: Mapped[str | None] = mapped_column(String(100), nullable=True)
    suplemento_valor_base: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    suplemento_valor_local: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 2), nullable=True
    )
    suplemento_editado_localmente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    suplemento_nota_cliente: Mapped[str | None] = mapped_column(Text, nullable=True)
    suplemento_quantidade: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("1"), server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
