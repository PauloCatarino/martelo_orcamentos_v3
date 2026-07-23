"""User SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.orcamento import Orcamento
    from app.models.orcamento_versao import OrcamentoVersao


class User(Base):
    """Application user."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    #: Área de trabalho (Orçamentação, Preparação (desenhos), Expedição...).
    #: Texto livre: o combo sugere valores mas aceita novos.
    departamento: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    created_orcamentos: Mapped[list["Orcamento"]] = relationship(
        "Orcamento",
        back_populates="created_by",
        foreign_keys="Orcamento.created_by_id",
    )
    updated_orcamentos: Mapped[list["Orcamento"]] = relationship(
        "Orcamento",
        back_populates="updated_by",
        foreign_keys="Orcamento.updated_by_id",
    )
    created_orcamento_versoes: Mapped[list["OrcamentoVersao"]] = relationship(
        "OrcamentoVersao",
        back_populates="created_by",
        foreign_keys="OrcamentoVersao.created_by_id",
    )
    updated_orcamento_versoes: Mapped[list["OrcamentoVersao"]] = relationship(
        "OrcamentoVersao",
        back_populates="updated_by",
        foreign_keys="OrcamentoVersao.updated_by_id",
    )
