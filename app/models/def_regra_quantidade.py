"""DefRegraQuantidade SQLAlchemy model (phase 8T.5.0)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DefRegraQuantidade(Base):
    """Configurable quantity rule: an expression over the main piece dimensions.

    The expression (evaluated by app.domain.regras_quantidade_expr) yields the
    quantity of a hardware item from COMP/LARG/ESP/QT_PAI. This phase only stores
    and validates the rules; wiring to components/costing comes later (8T.5.1).
    """

    __tablename__ = "def_regras_quantidade"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_regras_quantidade_codigo"),
        Index("ix_def_regras_quantidade_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    expressao: Mapped[str] = mapped_column(Text, nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
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
