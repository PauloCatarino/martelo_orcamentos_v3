"""DefMaquina SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.def_maquina_escalao_area import DefMaquinaEscalaoArea
    from app.models.def_operacao import DefOperacao


class DefMaquina(Base):
    """Reusable machine or work center definition."""

    __tablename__ = "def_maquinas"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_maquinas_codigo"),
        Index("ix_def_maquinas_tipo", "tipo"),
        Index("ix_def_maquinas_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Machine tariffs (phase 8S.0). custo_hora is the STD hourly rate; SERIE is the
    # batch rate. preco_ml: €/ml of perimeter (cut) or edging (orla). setup_peca:
    # fixed handling/setup cost per piece (€). Not every machine uses every tariff.
    custo_hora: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_hora_serie: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    preco_ml_std: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    preco_ml_serie: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_setup_peca_std: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    custo_setup_peca_serie: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    operacoes: Mapped[list["DefOperacao"]] = relationship(
        "DefOperacao",
        back_populates="maquina",
    )
    escaloes_area: Mapped[list["DefMaquinaEscalaoArea"]] = relationship(
        "DefMaquinaEscalaoArea",
        back_populates="maquina",
        cascade="all, delete-orphan",
    )
