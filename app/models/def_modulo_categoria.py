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
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DefModuloCategoria(Base):
    """One manageable category (or subcategory) of the module library.

    A row with ``parent_id`` NULL is a top-level category; with ``parent_id``
    set it is a subcategory of that parent (one level only — subcategories
    cannot themselves have subcategories).
    """

    __tablename__ = "def_modulo_categorias"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_modulo_categorias_codigo"),
        Index("ix_def_modulo_categorias_parent_id", "parent_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(60), nullable=False)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    # NULL = top-level category; set = subcategory of that category.
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("def_modulo_categorias.id"), nullable=True
    )
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
