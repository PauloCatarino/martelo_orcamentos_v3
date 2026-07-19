"""Locally edited effective operation of one costing line."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrcamentoItemCusteioLinhaOperacao(Base):
    """Materialized operation set used only after an explicit local edit."""

    __tablename__ = "orcamento_item_custeio_linha_operacoes"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    linha_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_item_custeio_linhas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    def_operacao_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("def_operacoes.id"), nullable=True, index=True
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    tipo_operacao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unidade_calculo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    maquina_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("def_maquinas.id"), nullable=True, index=True
    )
    origem: Mapped[str] = mapped_column(String(40), nullable=False, server_default="LOCAL")
    acao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    metodo_calculo: Mapped[str | None] = mapped_column(String(30), nullable=True, index=True)
    regra_calculo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantidade_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    rasgo_qt_comp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rasgo_qt_larg: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tempo_setup_minutos: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    tempo_por_unidade_minutos: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    unidade_tempo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    obrigatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
