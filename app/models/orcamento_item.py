"""OrcamentoItem SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.orcamento_item_modulo import OrcamentoItemModulo
    from app.models.orcamento_item_variavel import OrcamentoItemVariavel
    from app.models.orcamento_versao import OrcamentoVersao


class OrcamentoItem(Base):
    """Line item that belongs to one budget version."""

    __tablename__ = "orcamento_items"
    __table_args__ = (
        UniqueConstraint("orcamento_versao_id", "ordem", name="uq_orcamento_items_versao_ordem"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_versao_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_versoes.id"),
        nullable=False,
        index=True,
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    tipo_item: Mapped[str] = mapped_column(String(50), nullable=False, default="OUTRO", server_default="OUTRO")
    item: Mapped[str] = mapped_column(String(255), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    altura: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    largura: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    profundidade: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    quantidade: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unidade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    preco_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    preco_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    ajuste: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    # Per-item production type exception: NULL inherits the version's
    # tipo_producao_default; 'STD'/'SERIE' overrides it (phase 8S.4).
    tipo_producao: Mapped[str | None] = mapped_column(String(10), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    orcamento_versao: Mapped["OrcamentoVersao"] = relationship(
        "OrcamentoVersao",
        back_populates="itens",
    )
    variaveis: Mapped[list["OrcamentoItemVariavel"]] = relationship(
        "OrcamentoItemVariavel",
        back_populates="item",
    )
    modulos: Mapped[list["OrcamentoItemModulo"]] = relationship(
        "OrcamentoItemModulo",
        back_populates="item",
    )
