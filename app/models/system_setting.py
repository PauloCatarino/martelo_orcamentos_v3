"""SystemSetting SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SystemSetting(Base):
    """Configurable system-level setting used by Martelo V3."""

    __tablename__ = "system_settings"
    __table_args__ = (
        UniqueConstraint("chave", name="uq_system_settings_chave"),
        Index("ix_system_settings_grupo", "grupo"),
        Index("ix_system_settings_tipo", "tipo"),
        Index("ix_system_settings_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chave: Mapped[str] = mapped_column(String(100), nullable=False)
    valor: Mapped[str | None] = mapped_column(Text, nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False, default="texto", server_default="texto")
    grupo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
