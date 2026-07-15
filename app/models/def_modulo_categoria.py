"""Manageable categories of the module library (phase 6).

Categories were a fixed set (ROUPEIROS/COZINHAS/MOVEIS_WC/OUTROS); they now
live in this table so the user can create new ones (e.g. a customer name),
rename, archive and safely delete them. Modules keep referencing the category
by its ``codigo`` (string), which preserves every existing module.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DefModuloCategoria(Base):
    """One manageable category of the module library."""

    __tablename__ = "def_modulo_categorias"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_modulo_categorias_codigo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    # Archived categories stay on old modules but leave the pickers.
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
