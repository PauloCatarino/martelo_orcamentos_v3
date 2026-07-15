"""PHC orders of a budget version (phase 5 — multiple PHC orders).

A budget version may be adjudicated through several PHC orders. Each order
number lives in this child table; exactly one of them is the "principal"
order, mirrored into ``orcamento_versoes.enc_phc`` for compatibility with
existing listings and reports.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrcamentoVersaoEncomendaPhc(Base):
    """One PHC order number of a budget version."""

    __tablename__ = "orcamento_versao_encomendas_phc"
    __table_args__ = (
        UniqueConstraint(
            "orcamento_versao_id",
            "numero",
            name="uq_versao_encomenda_phc_numero",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_versao_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_versoes.id"),
        nullable=False,
        index=True,
    )
    numero: Mapped[str] = mapped_column(String(64), nullable=False)
    is_principal: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
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
