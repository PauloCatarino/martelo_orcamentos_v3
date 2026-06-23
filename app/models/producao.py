"""Producao SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Producao(Base):
    """Production process imported from the legacy V2 workflow."""

    __tablename__ = "producao"
    __table_args__ = (
        UniqueConstraint("codigo_processo", name="uq_producao_codigo"),
        UniqueConstraint(
            "ano",
            "num_enc_phc",
            "versao_obra",
            "versao_plano",
            name="uq_producao_chave",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo_processo: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    ano: Mapped[str] = mapped_column(String(4), nullable=False, index=True)
    num_enc_phc: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    versao_obra: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        server_default="01",
    )
    versao_plano: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        server_default="01",
    )
    orcamento_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("orcamentos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    cliente_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("clientes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    responsavel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    estado: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    nome_cliente: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    nome_cliente_simplex: Mapped[str | None] = mapped_column(String(255), nullable=True)
    num_cliente_phc: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ref_cliente: Mapped[str | None] = mapped_column(String(64), nullable=True)
    num_orcamento: Mapped[str | None] = mapped_column(String(16), nullable=True)
    versao_orc: Mapped[str | None] = mapped_column(String(2), nullable=True)
    obra: Mapped[str | None] = mapped_column(String(255), nullable=True)
    localizacao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    descricao_orcamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    data_inicio: Mapped[str | None] = mapped_column(String(10), nullable=True)
    data_entrega: Mapped[str | None] = mapped_column(String(10), nullable=True)
    preco_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    qt_artigos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    descricao_artigos: Mapped[str | None] = mapped_column(Text, nullable=True)
    materias_usados: Mapped[str | None] = mapped_column(Text, nullable=True)
    descricao_producao: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas1: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas2: Mapped[str | None] = mapped_column(Text, nullable=True)
    notas3: Mapped[str | None] = mapped_column(Text, nullable=True)
    imagem_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    pasta_servidor: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    tipo_pasta: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
