"""OrcamentoItemVariavel SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.orcamento_item import OrcamentoItem


class OrcamentoItemVariavel(Base):
    """Variable attached to one budget line item."""

    __tablename__ = "orcamento_item_variaveis"
    __table_args__ = (
        UniqueConstraint("item_id", "nome", name="uq_orcamento_item_variaveis_item_nome"),
        UniqueConstraint("item_id", "ordem", name="uq_orcamento_item_variaveis_item_ordem"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_items.id"),
        nullable=False,
        index=True,
    )
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    valor: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    unidade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    item: Mapped["OrcamentoItem"] = relationship(
        "OrcamentoItem",
        back_populates="variaveis",
    )
