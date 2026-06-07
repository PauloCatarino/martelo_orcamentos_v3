"""OrcamentoItemValuesetLinha SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.def_materia_prima import DefMateriaPrima
    from app.models.orcamento_item import OrcamentoItem


class OrcamentoItemValuesetLinha(Base):
    """One ValueSet line assigned to a budget item."""

    __tablename__ = "orcamento_item_valueset_linhas"
    __table_args__ = (
        UniqueConstraint(
            "orcamento_item_id",
            "chave",
            "codigo_opcao",
            name="uq_orcamento_item_valueset_linhas_item_chave_opcao",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_items.id"),
        nullable=False,
        index=True,
    )
    chave: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    codigo_opcao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nome_opcao: Mapped[str | None] = mapped_column(String(150), nullable=True)
    padrao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
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
    herdado_do_orcamento: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
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

    orcamento_item: Mapped["OrcamentoItem"] = relationship(
        "OrcamentoItem",
        foreign_keys=[orcamento_item_id],
    )
    materia_prima: Mapped["DefMateriaPrima | None"] = relationship(
        "DefMateriaPrima",
        foreign_keys=[materia_prima_id],
    )
