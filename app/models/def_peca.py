"""DefPeca SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.peca_types import SIMPLES


class DefPeca(Base):
    """Reusable piece definition from the technical catalog."""

    __tablename__ = "def_pecas"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_pecas_codigo"),
        Index("ix_def_pecas_nome", "nome"),
        Index("ix_def_pecas_grupo", "grupo"),
        Index("ix_def_pecas_tipo_peca", "tipo_peca"),
        Index("ix_def_pecas_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(100), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    grupo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_peca: Mapped[str] = mapped_column(String(50), nullable=False, default=SIMPLES, server_default=SIMPLES)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
