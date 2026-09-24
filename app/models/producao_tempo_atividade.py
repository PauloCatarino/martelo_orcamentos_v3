"""Tempo ativo no iMos e na Lista Material, por encomenda, pessoa e dia."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProducaoTempoAtividade(Base):
    """Segundos realmente ativos numa encomenda iMos, num programa, num dia.

    Guarda-se o nome da encomenda tal como aparece na janela, e não a obra:
    a ligação à linha da Produção faz-se na leitura. Assim nada se perde se a
    obra ainda não existir, ou se o nome só bater mais tarde.
    """

    __tablename__ = "producao_tempo_atividade"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "programa",
            "nome_encomenda",
            "dia",
            name="uq_prod_tempo_user_prog_enc_dia",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )
    #: ``imos`` (desenho) ou ``excel`` (Lista Material).
    programa: Mapped[str] = mapped_column(String(10), nullable=False)
    nome_encomenda: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    dia: Mapped[date] = mapped_column(Date, nullable=False)
    segundos: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
