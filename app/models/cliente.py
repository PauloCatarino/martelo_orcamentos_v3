"""Cliente SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.orcamento import Orcamento


class Cliente(Base):
    """Commercial customer."""

    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    nome_simplex: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(255), nullable=True)
    telemovel: Mapped[str | None] = mapped_column(String(255), nullable=True)
    morada: Mapped[str | None] = mapped_column(Text, nullable=True)
    pagina_web: Mapped[str | None] = mapped_column(String(255), nullable=True)
    num_cliente_phc: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    source_system: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_temporary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    info_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    info_2: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    orcamentos: Mapped[list["Orcamento"]] = relationship(
        "Orcamento",
        back_populates="cliente",
    )
