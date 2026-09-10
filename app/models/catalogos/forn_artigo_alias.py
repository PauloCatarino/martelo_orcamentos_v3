"""Outras maneiras de chamar ao mesmo artigo.

Código de barras, referência do fabricante, referência antiga, referência que o
fornecedor usa nas faturas. Sem isto a pesquisa falha sempre que alguém procura
pelo código que tem à frente em vez daquele que ficou no catálogo — que é
metade das vezes.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.catalogos import SCHEMA_CATALOGOS, CatalogosBase

#: Valores de ``tipo``.
ALIAS_EAN = "EAN"
ALIAS_FABRICANTE = "FABRICANTE"
ALIAS_ANTIGA = "ANTIGA"
ALIAS_CLIENTE = "CLIENTE"


class FornArtigoAlias(CatalogosBase):
    """Uma referência alternativa de um artigo de catálogo."""

    __tablename__ = "forn_artigos_aliases"
    __table_args__ = (
        UniqueConstraint(
            "artigo_id", "tipo", "valor", name="uq_forn_artigos_aliases_valor"
        ),
        Index("ix_forn_artigos_aliases_valor", "valor"),
        Index("ix_forn_artigos_aliases_artigo", "artigo_id"),
        {"schema": SCHEMA_CATALOGOS},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    artigo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(f"{SCHEMA_CATALOGOS}.forn_artigos.id", ondelete="CASCADE"),
        nullable=False,
    )
    #: EAN | FABRICANTE | ANTIGA | CLIENTE (constantes deste módulo).
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    valor: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    artigo: Mapped["FornArtigo"] = relationship(  # noqa: F821
        "FornArtigo", lazy="raise"
    )
