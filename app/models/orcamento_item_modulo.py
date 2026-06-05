"""OrcamentoItemModulo SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.orcamento_item import OrcamentoItem


class OrcamentoItemModulo(Base):
    """Module associated with one budget item."""

    __tablename__ = "orcamento_item_modulos"
    __table_args__ = (
        UniqueConstraint("orcamento_item_id", "ordem", name="uq_orcamento_item_modulos_item_ordem"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_items.id"),
        nullable=False,
        index=True,
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    altura: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    largura: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    profundidade: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=Decimal("1"),
        server_default="1",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    item: Mapped["OrcamentoItem"] = relationship(
        "OrcamentoItem",
        back_populates="modulos",
    )
