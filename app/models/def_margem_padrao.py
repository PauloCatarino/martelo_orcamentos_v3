"""DefMargemPadrao SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.user import User


class DefMargemPadrao(Base):
    """Default margins applied as the INITIAL values of new budgets.

    One record per scope: a single STANDARD (enforced in the service), one per
    customer and one per user (unique constraints; MySQL allows multiple NULLs,
    so the STANDARD rows are not bound by them). Inside each budget the user
    keeps editing the version margins freely.
    """

    __tablename__ = "def_margens_padrao"
    __table_args__ = (
        UniqueConstraint("cliente_id", name="uq_def_margens_padrao_cliente"),
        UniqueConstraint("user_id", name="uq_def_margens_padrao_user"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 'STANDARD' | 'CLIENTE' | 'UTILIZADOR' (see app.domain.margens_padrao_types).
    ambito: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    cliente_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("clientes.id"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    margem_lucro_pct: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    margem_mp_pct: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    margem_mao_obra_pct: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    margem_acabamentos_pct: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    custos_administrativos_pct: Mapped[Decimal] = mapped_column(
        Numeric(8, 4), nullable=False, default=Decimal("0"), server_default="0"
    )
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    cliente: Mapped["Cliente | None"] = relationship(
        "Cliente",
        foreign_keys=[cliente_id],
    )
    user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
