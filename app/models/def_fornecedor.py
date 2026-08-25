"""Supplier of raw materials.

Until now the supplier was just text on the material row, which was enough to
read but not enough to *do* anything — namely to ask for updated prices. Each
supplier here carries the address the request should go to.

A supplier usually has several mailboxes (comercial, encomendas, a pessoa que
costuma responder). The ``email`` kept here is the **suggestion**: at send time
the user sees it, can change it and can add a CC.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DefFornecedor(Base):
    """One supplier of raw materials."""

    __tablename__ = "def_fornecedores"
    __table_args__ = (
        UniqueConstraint("nome", name="uq_def_fornecedores_nome"),
        Index("ix_def_fornecedores_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email_cc: Mapped[str | None] = mapped_column(String(255), nullable=True)
    pessoa_contacto: Mapped[str | None] = mapped_column(String(150), nullable=True)
    telefone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
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
