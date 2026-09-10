"""Histórico de preços de um artigo de catálogo.

Uma linha por preço observado, ligada à tabela que o trouxe. Nada aqui é
reescrito: é o mesmo princípio de ``def_materias_primas_precos_historico``, mas
do lado dos catálogos — é o que permite responder a "quanto subiu este perfil
desde a tabela de 2024" em vez de só saber o preço de hoje.

A ``referencia`` vem copiada de propósito, para o histórico continuar legível
mesmo que o artigo seja mais tarde renumerado ou desativado.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.catalogos import SCHEMA_CATALOGOS, CatalogosBase


class FornArtigoPreco(CatalogosBase):
    """Um preço registado de um artigo de catálogo."""

    __tablename__ = "forn_artigos_precos"
    __table_args__ = (
        Index("ix_forn_artigos_precos_artigo", "artigo_id"),
        Index("ix_forn_artigos_precos_tabela", "tabela_preco_id"),
        Index("ix_forn_artigos_precos_referencia", "referencia"),
        {"schema": SCHEMA_CATALOGOS},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    artigo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA_CATALOGOS}.forn_artigos.id", ondelete="CASCADE"),
        nullable=False,
    )
    tabela_preco_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA_CATALOGOS}.forn_tabelas_precos.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: Copiada para o histórico sobreviver ao artigo.
    referencia: Mapped[str | None] = mapped_column(String(120), nullable=True)
    #: Nulo quando a tabela lista o artigo mas não lhe dá preço (acontece).
    valor: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, server_default="EUR")
    unidade: Mapped[str] = mapped_column(String(10), nullable=False, server_default="UN")
    #: Desconto de tabela, quando o fornecedor o pratica (em %).
    desconto: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    valido_de: Mapped[date | None] = mapped_column(Date, nullable=True)
    valido_ate: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    artigo: Mapped["FornArtigo"] = relationship(  # noqa: F821
        "FornArtigo", lazy="raise"
    )
    tabela: Mapped["FornTabelaPreco"] = relationship(  # noqa: F821
        "FornTabelaPreco", lazy="raise"
    )
