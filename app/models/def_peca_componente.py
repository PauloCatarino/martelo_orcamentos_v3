"""DefPecaComponente SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.componente_types import PECA

if TYPE_CHECKING:
    from app.models.def_peca import DefPeca


class DefPecaComponente(Base):
    """Component associated with one composite piece definition."""

    __tablename__ = "def_peca_componentes"
    __table_args__ = (
        UniqueConstraint("def_peca_pai_id", "ordem", name="uq_def_peca_componentes_pai_ordem"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    def_peca_pai_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("def_pecas.id"),
        nullable=False,
        index=True,
    )
    tipo_componente: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PECA,
        server_default=PECA,
        index=True,
    )
    def_peca_componente_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_pecas.id"),
        nullable=True,
        index=True,
    )
    referencia_componente: Mapped[str | None] = mapped_column(String(150), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=Decimal("1"),
        server_default="1",
    )
    regra_quantidade: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default="FIXA",
        server_default="FIXA",
    )
    obrigatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def_peca_pai: Mapped["DefPeca"] = relationship(
        "DefPeca",
        back_populates="componentes",
        foreign_keys=[def_peca_pai_id],
    )
    def_peca_componente: Mapped["DefPeca | None"] = relationship(
        "DefPeca",
        foreign_keys=[def_peca_componente_id],
    )
