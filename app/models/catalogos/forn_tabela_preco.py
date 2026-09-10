"""Uma tabela de preços tal como o fornecedor a enviou.

Cada ficheiro que chega — um xlsx da Emuca, um PDF T-04 da Balbino & Faustino,
um export do site da Casa Trend — dá origem a uma linha aqui. O ``ficheiro_hash``
é o que torna a importação repetível sem estragos: reimportar o mesmo ficheiro
não faz nada, e um ficheiro novo gera apenas as diferenças de preço.

Nada aqui aponta para ``def_fornecedores``: o fornecedor fica como texto, e é
essa ausência de chave estrangeira que permite reconstruir os catálogos do zero
sem tocar nos orçamentos.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.catalogos import SCHEMA_CATALOGOS, CatalogosBase


class FornTabelaPreco(CatalogosBase):
    """Uma tabela de preços recebida de um fornecedor."""

    __tablename__ = "forn_tabelas_precos"
    __table_args__ = (
        # Nulo é permitido (ficheiros sem hash calculado), mas dois ficheiros
        # com o mesmo conteúdo nunca entram duas vezes.
        UniqueConstraint("ficheiro_hash", name="uq_forn_tabelas_precos_hash"),
        Index("ix_forn_tabelas_precos_fornecedor", "fornecedor"),
        Index("ix_forn_tabelas_precos_ativa", "ativa"),
        Index("ix_forn_tabelas_precos_data", "data_tabela"),
        {"schema": SCHEMA_CATALOGOS},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    #: Quem vende. Texto, não chave estrangeira — ver o módulo app.db.catalogos.
    fornecedor: Mapped[str] = mapped_column(String(150), nullable=False)
    #: A marca, quando não é o próprio fornecedor (Innovus vendido pela B&F).
    fabricante: Mapped[str | None] = mapped_column(String(150), nullable=True)
    nome: Mapped[str] = mapped_column(String(200), nullable=False)
    #: A referência que o fornecedor dá à tabela ("T-04", "BF-82A").
    referencia_tabela: Mapped[str | None] = mapped_column(String(60), nullable=True)
    #: A data que vem impressa na tabela, não a da importação.
    data_tabela: Mapped[date | None] = mapped_column(Date, nullable=True)
    ficheiro_origem: Mapped[str | None] = mapped_column(String(400), nullable=True)
    ficheiro_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    moeda: Mapped[str] = mapped_column(String(3), nullable=False, server_default="EUR")
    #: Unidade dominante da tabela: UN, ML ou M2 (as placas vendem-se ao m²).
    unidade_preco: Mapped[str | None] = mapped_column(String(10), nullable=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    #: Uma tabela substituída fica cá, mas deixa de ser a que vale.
    ativa: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    importada_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
