"""Característica estruturada de um módulo de roupeiro."""

from __future__ import annotations
from decimal import Decimal
from sqlalchemy import BigInteger, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class DefModuloCaracteristica(Base):
    __tablename__ = "def_modulo_caracteristicas"
    __table_args__ = (UniqueConstraint("def_modulo_id", "codigo", name="uq_def_mod_car_mod_cod"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    def_modulo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("def_modulos.id", ondelete="CASCADE"), nullable=False, index=True
    )
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(12, 3), nullable=False, default=Decimal("1"), server_default="1"
    )
    modulo = relationship("DefModulo", back_populates="caracteristicas")
