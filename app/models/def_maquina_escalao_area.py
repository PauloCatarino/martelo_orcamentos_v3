"""DefMaquinaEscalaoArea SQLAlchemy model (CNC area price tiers, phase 8S.0)."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.def_maquina import DefMaquina


class DefMaquinaEscalaoArea(Base):
    """Area-based price tier for a (CNC) machine.

    Each tier applies to pieces with an area up to ``area_max_m2`` (the last tier
    may have ``area_max_m2`` NULL meaning "no upper limit"). The price is per
    piece, with STD and SERIE variants.
    """

    __tablename__ = "def_maquina_escaloes_area"
    __table_args__ = (
        Index("ix_def_maquina_escaloes_area_maquina", "def_maquina_id"),
        Index("ix_def_maquina_escaloes_area_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    def_maquina_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("def_maquinas.id"),
        nullable=False,
        index=True,
    )
    nivel: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    area_max_m2: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    preco_peca_std: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    preco_peca_serie: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
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

    maquina: Mapped["DefMaquina"] = relationship(
        "DefMaquina",
        back_populates="escaloes_area",
    )
