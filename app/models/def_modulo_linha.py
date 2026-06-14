"""DefModuloLinha SQLAlchemy model (phase 8U.0).

One structural line inside a reusable module. Holds ONLY the parametric
structure (type, piece, measure formulas as text, ValueSet key, orla code,
quantity rule, composite parent by order). No material / price / orla-cost /
real-dimension snapshot — those re-resolve on import.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.custeio_linha_types import PECA

if TYPE_CHECKING:
    from app.models.def_modulo import DefModulo


class DefModuloLinha(Base):
    """One structural line of a reusable module."""

    __tablename__ = "def_modulo_linhas"
    __table_args__ = (
        Index("ix_def_modulo_linhas_def_modulo_id", "def_modulo_id"),
        Index("ix_def_modulo_linhas_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    def_modulo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("def_modulos.id", ondelete="CASCADE"),
        nullable=False,
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    # DIVISAO_INDEPENDENTE / PECA / PECA_COMPOSTA / FERRAGEM / OPERACAO
    # (see app.domain.custeio_linha_types).
    tipo_linha: Mapped[str] = mapped_column(
        String(30), nullable=False, default=PECA, server_default=PECA
    )
    def_peca_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("def_pecas.id"), nullable=True
    )
    def_peca_codigo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    codigo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descricao_livre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Quantities and measures as TEXT, to keep formulas/variables (H, L/3, HM...).
    qt_mod: Mapped[str | None] = mapped_column(String(50), nullable=True)
    qt_und: Mapped[str | None] = mapped_column(String(50), nullable=True)
    comp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    larg: Mapped[str | None] = mapped_column(String(100), nullable=True)
    esp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chave_valueset: Mapped[str | None] = mapped_column(String(100), nullable=True)
    codigo_orlas: Mapped[str | None] = mapped_column(String(10), nullable=True)
    def_regra_quantidade_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("def_regras_quantidade.id"), nullable=True
    )
    # Composite parent/child relation WITHIN the module, by order (resolved on
    # insertion into a real item costing).
    linha_pai_ordem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nivel: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
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

    modulo: Mapped["DefModulo"] = relationship(
        "DefModulo",
        back_populates="linhas",
    )
