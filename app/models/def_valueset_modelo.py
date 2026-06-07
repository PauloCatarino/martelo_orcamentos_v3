"""DefValuesetModelo SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.def_valueset_modelo_linha import DefValuesetModeloLinha


class DefValuesetModelo(Base):
    """Reusable ValueSet model / library entry."""

    __tablename__ = "def_valueset_modelos"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_valueset_modelos_codigo"),
        Index("ix_def_valueset_modelos_codigo", "codigo"),
        Index("ix_def_valueset_modelos_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(100), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ambito: Mapped[str] = mapped_column(
        String(30), nullable=False, default="UTILIZADOR", server_default="UTILIZADOR"
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True, index=True
    )
    visivel_para_todos: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
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

    linhas: Mapped[list["DefValuesetModeloLinha"]] = relationship(
        "DefValuesetModeloLinha",
        back_populates="modelo",
    )
