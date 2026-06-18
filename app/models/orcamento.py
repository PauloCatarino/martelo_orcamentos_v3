"""Orcamento SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.cliente import Cliente
    from app.models.orcamento_versao import OrcamentoVersao
    from app.models.user import User


class Orcamento(Base):
    """Stable commercial budget record."""

    __tablename__ = "orcamentos"
    __table_args__ = (
        UniqueConstraint("ano", "num_orcamento", name="uq_orcamentos_ano_num_orcamento"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ano: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    num_orcamento: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    cliente_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("clientes.id"),
        nullable=False,
        index=True,
    )
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    obra: Mapped[str | None] = mapped_column(String(255), nullable=True)
    localizacao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ref_cliente: Mapped[str | None] = mapped_column(String(255), nullable=True)
    info_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    info_2: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    cliente: Mapped["Cliente"] = relationship(
        "Cliente",
        back_populates="orcamentos",
    )
    versoes: Mapped[list["OrcamentoVersao"]] = relationship(
        "OrcamentoVersao",
        back_populates="orcamento",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        back_populates="created_orcamentos",
        foreign_keys=[created_by_id],
    )
    updated_by: Mapped["User | None"] = relationship(
        "User",
        back_populates="updated_orcamentos",
        foreign_keys=[updated_by_id],
    )
