"""O artigo tal como o fornecedor o vende.

Uma linha por coisa encomendável. Para ferragens isso é a referência e pouco
mais; para placas é a combinação **referência × substrato × espessura**, porque
é essa que tem preço próprio — um aglomerado de 19 mm e um de 8 mm da mesma
referência são dois artigos, não duas colunas do mesmo.

É esse desdobramento que permite perguntar "quanto custa o 19 mm em qualquer
fornecedor" sem ter de saber em que coluna do Excel de cada um é que ele estava.

O artigo não pertence a nenhuma tabela de preços: sobrevive-lhes. Quem se liga a
uma tabela é o preço (``forn_artigos_precos``).

Os atributos que só alguns fornecedores têm — Módulo, Acabamento, Cap. kg, V(L)
na Casa Trend — ficam em ``atributos``, para não haver uma coluna por fornecedor.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
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

from app.db.catalogos import SCHEMA_CATALOGOS, CatalogosBase


class FornArtigo(CatalogosBase):
    """Um artigo de catálogo de fornecedor."""

    __tablename__ = "forn_artigos"
    __table_args__ = (
        # A chave natural é construída pelo adaptador de cada fornecedor: é ela
        # que decide o que conta como "o mesmo artigo" numa reimportação. Para
        # ferragens costuma ser a referência; para placas, referência +
        # substrato + espessura.
        UniqueConstraint(
            "fornecedor", "chave_natural", name="uq_forn_artigos_chave_natural"
        ),
        Index("ix_forn_artigos_referencia", "referencia"),
        Index("ix_forn_artigos_fornecedor", "fornecedor"),
        Index("ix_forn_artigos_familia", "familia"),
        Index("ix_forn_artigos_grupo", "grupo"),
        Index("ix_forn_artigos_substrato", "substrato"),
        Index("ix_forn_artigos_espessura", "espessura_mm"),
        Index("ix_forn_artigos_ativo", "ativo"),
        {"schema": SCHEMA_CATALOGOS},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    fornecedor: Mapped[str] = mapped_column(String(150), nullable=False)
    fabricante: Mapped[str | None] = mapped_column(String(150), nullable=True)
    #: O que o adaptador considera identificar o artigo dentro do fornecedor.
    chave_natural: Mapped[str] = mapped_column(String(300), nullable=False)

    referencia: Mapped[str] = mapped_column(String(120), nullable=False)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    #: Nome do decorativo, quando existe ("Etna Oak", "Special White").
    nome_design: Mapped[str | None] = mapped_column(String(200), nullable=True)
    #: UN (unidade), ML (metro linear) ou M2 (metro quadrado).
    unidade: Mapped[str] = mapped_column(String(10), nullable=False, server_default="UN")

    familia: Mapped[str | None] = mapped_column(String(200), nullable=True)
    seccao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    #: Código de catálogo do fornecedor ("05.04.01" na Casa Trend).
    catalogo: Mapped[str | None] = mapped_column(String(60), nullable=True)
    pagina: Mapped[str | None] = mapped_column(String(20), nullable=True)
    #: Grupo de preço, quando o fornecedor os usa ("INNOVUS I - GRUPO 1").
    grupo: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # --- placas ---------------------------------------------------------
    #: Núcleo da placa: PB STD, PB HID, MDF STD CARB2, ...
    substrato: Mapped[str | None] = mapped_column(String(80), nullable=True)
    espessura_mm: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    acabamento: Mapped[str | None] = mapped_column(String(60), nullable=True)
    #: Formatos em que existe ("2800x2070 e 2750x1830").
    formatos: Mapped[str | None] = mapped_column(String(200), nullable=True)

    atributos: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
