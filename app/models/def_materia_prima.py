"""DefMateriaPrima SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ORIGEM_DADOS_EXCEL = "EXCEL"


class DefMateriaPrima(Base):
    """Internal raw material / hardware catalog entry for the Martelo V3."""

    __tablename__ = "def_materias_primas"
    __table_args__ = (
        # The unique constraint also indexes ref_le. MySQL allows multiple NULLs,
        # so rows without ref_le are not blocked.
        UniqueConstraint("ref_le", name="uq_def_materias_primas_ref_le"),
        Index("ix_def_materias_primas_tipo_martelo", "tipo_martelo"),
        Index("ix_def_materias_primas_familia_martelo", "familia_martelo"),
        Index("ix_def_materias_primas_tipo_original_excel", "tipo_original_excel"),
        Index("ix_def_materias_primas_familia_original_excel", "familia_original_excel"),
        Index("ix_def_materias_primas_ativo", "ativo"),
        Index("ix_def_materias_primas_origem_dados", "origem_dados"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    ref_le: Mapped[str | None] = mapped_column(String(100), nullable=True)
    referencia_fornecedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    tipo_original_excel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    familia_original_excel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_martelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    familia_martelo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unidade: Mapped[str | None] = mapped_column(String(30), nullable=True)
    preco_tabela: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    desconto: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    margem: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    preco_liquido: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    comprimento: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    largura: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    espessura: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    fornecedor: Mapped[str | None] = mapped_column(String(150), nullable=True)
    origem_dados: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=ORIGEM_DADOS_EXCEL,
        server_default=ORIGEM_DADOS_EXCEL,
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
