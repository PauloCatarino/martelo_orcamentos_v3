"""DefValuesetChave SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DefValuesetChave(Base):
    """Configurable ValueSet key/category."""

    __tablename__ = "def_valueset_chaves"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_valueset_chaves_codigo"),
        Index("ix_def_valueset_chaves_tipo", "tipo"),
        Index("ix_def_valueset_chaves_grupo", "grupo"),
        Index("ix_def_valueset_chaves_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(100), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    grupo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sistema: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
