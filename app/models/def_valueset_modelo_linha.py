"""DefValuesetModeloLinha SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.def_materia_prima import DefMateriaPrima
    from app.models.def_valueset_modelo import DefValuesetModelo


class DefValuesetModeloLinha(Base):
    """One ValueSet line inside a reusable model."""

    __tablename__ = "def_valueset_modelo_linhas"
    __table_args__ = (
        UniqueConstraint(
            "def_valueset_modelo_id",
            "chave",
            name="uq_def_valueset_modelo_linhas_modelo_chave",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    def_valueset_modelo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("def_valueset_modelos.id"),
        nullable=False,
        index=True,
    )
    chave: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    materia_prima_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_materias_primas.id"),
        nullable=True,
        index=True,
    )
    ref_materia_prima: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descricao_materia_prima: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem: Mapped[str | None] = mapped_column(String(100), nullable=True)
    editado_localmente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    modelo: Mapped["DefValuesetModelo"] = relationship(
        "DefValuesetModelo",
        back_populates="linhas",
    )
    materia_prima: Mapped["DefMateriaPrima | None"] = relationship(
        "DefMateriaPrima",
        foreign_keys=[materia_prima_id],
    )
