"""DefModulo SQLAlchemy model (phase 8U.0).

A reusable module/article template: only the PARAMETRIC STRUCTURE (pieces,
components, independent divisions, measure formulas, ValueSet key, orla code,
quantity-rule link, operations) — never material/price (those re-resolve from
the destination item's ValueSet on import).
"""

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
from app.domain.modulo_categorias import AMBITO_UTILIZADOR, OUTROS

if TYPE_CHECKING:
    from app.models.def_modulo_linha import DefModuloLinha
    from app.models.user import User


class DefModulo(Base):
    """Reusable module/article template (header)."""

    __tablename__ = "def_modulos"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_modulos_codigo"),
        Index("ix_def_modulos_ambito", "ambito"),
        Index("ix_def_modulos_categoria", "categoria"),
        Index("ix_def_modulos_subcategoria", "subcategoria"),
        Index("ix_def_modulos_user_id", "user_id"),
        Index("ix_def_modulos_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(100), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'UTILIZADOR' (own user) | 'GLOBAL' (everyone) — see app.domain.modulo_categorias.
    ambito: Mapped[str] = mapped_column(
        String(20), nullable=False, default=AMBITO_UTILIZADOR, server_default=AMBITO_UTILIZADOR
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=True
    )
    # ROUPEIROS / COZINHAS / MOVEIS_WC / OUTROS (extensible).
    categoria: Mapped[str] = mapped_column(
        String(30), nullable=False, default=OUTROS, server_default=OUTROS
    )
    # Optional subcategory (codigo of a category whose parent is `categoria`).
    subcategoria: Mapped[str | None] = mapped_column(String(60), nullable=True)
    imagem_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
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

    user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    linhas: Mapped[list["DefModuloLinha"]] = relationship(
        "DefModuloLinha",
        back_populates="modulo",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
