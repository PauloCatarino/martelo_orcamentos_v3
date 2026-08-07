"""Memória privada do assistente de orçamentos."""

from __future__ import annotations
from datetime import datetime
from decimal import Decimal
from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class IaOrcamentoAnalise(Base):
    __tablename__ = "ia_orcamento_analises"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    orcamento_item_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("orcamento_items.id"), nullable=False, index=True)
    documento_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    documento_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    pagina: Mapped[int] = mapped_column(Integer, nullable=False)
    zona_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    fornecedor: Mapped[str] = mapped_column(String(50), nullable=False)
    modelo: Mapped[str] = mapped_column(String(150), nullable=False)
    resultado_json: Mapped[str] = mapped_column(Text, nullable=False)
    altura_confirmada_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    largura_confirmada_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    profundidade_confirmada_mm: Mapped[Decimal | None] = mapped_column(Numeric(12, 3), nullable=True)
    caracteristicas_confirmadas_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(30), nullable=False, default="ANALISADA", server_default="ANALISADA")
    erro: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    propostas = relationship("IaOrcamentoProposta", back_populates="analise")


class IaOrcamentoProposta(Base):
    __tablename__ = "ia_orcamento_propostas"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    analise_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ia_orcamento_analises.id"), nullable=False, index=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, index=True)
    posicao_top3: Mapped[int] = mapped_column(Integer, nullable=False)
    pontuacao: Mapped[float] = mapped_column(Float, nullable=False)
    explicacao: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposta_original_json: Mapped[str] = mapped_column(Text, nullable=False)
    correcoes_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    decisao: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDENTE", server_default="PENDENTE")
    motivo_rejeicao: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    analise = relationship("IaOrcamentoAnalise", back_populates="propostas")
    componentes = relationship("IaOrcamentoPropostaModulo", back_populates="proposta")


class IaOrcamentoPropostaModulo(Base):
    __tablename__ = "ia_orcamento_proposta_modulos"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    proposta_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("ia_orcamento_propostas.id"), nullable=False, index=True)
    def_modulo_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("def_modulos.id"), nullable=True, index=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    codigo_snapshot: Mapped[str] = mapped_column(String(100), nullable=False)
    nome_snapshot: Mapped[str] = mapped_column(String(150), nullable=False)
    largura_mm: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    espelhado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    proposta = relationship("IaOrcamentoProposta", back_populates="componentes")
