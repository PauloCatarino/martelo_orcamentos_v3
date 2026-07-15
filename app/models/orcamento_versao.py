"""OrcamentoVersao SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.orcamento import Orcamento
    from app.models.orcamento_item import OrcamentoItem
    from app.models.user import User


class OrcamentoVersao(Base):
    """Independent version of a budget."""

    __tablename__ = "orcamento_versoes"
    __table_args__ = (
        UniqueConstraint("orcamento_id", "numero_versao", name="uq_orcamento_versoes_orcamento_numero"),
        UniqueConstraint("codigo_versao", name="uq_orcamento_versoes_codigo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamentos.id"),
        nullable=False,
        index=True,
    )
    numero_versao: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo_versao: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    estado: Mapped[str] = mapped_column(String(50), nullable=False)
    enc_phc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    preco_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    preco_origem: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # Budget-level margins (phase 8T.0), human percentages (15 = 15%), applied
    # per cost block when building each item's price from its cost lines.
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
    # Selected source for "Repor Padrão"; the copied values above remain
    # editable locally in the budget version.
    perfil_margens: Mapped[str] = mapped_column(
        String(20), nullable=False, default="STANDARD", server_default="STANDARD"
    )
    # Production type applied to all the version items ('STD'/'SERIE'); each item
    # may override it with its own tipo_producao (phase 8S.4).
    tipo_producao_default: Mapped[str] = mapped_column(
        String(10), nullable=False, default="STD", server_default="STD"
    )
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
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

    orcamento: Mapped["Orcamento"] = relationship(
        "Orcamento",
        back_populates="versoes",
    )
    itens: Mapped[list["OrcamentoItem"]] = relationship(
        "OrcamentoItem",
        back_populates="orcamento_versao",
    )
    created_by: Mapped["User | None"] = relationship(
        "User",
        back_populates="created_orcamento_versoes",
        foreign_keys=[created_by_id],
    )
    updated_by: Mapped["User | None"] = relationship(
        "User",
        back_populates="updated_orcamento_versoes",
        foreign_keys=[updated_by_id],
    )
