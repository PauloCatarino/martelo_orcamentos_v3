"""Dicionário da casa: palavras que o corretor ortográfico aceita.

Partilhado por todos (decisão do Paulo, 16-09-2026). O dicionário do Windows
não conhece a linguagem da marcenaria — ilharga está lá, termolaminado não — e
cada palavra que alguém acrescenta deixa de aparecer sublinhada a toda a gente.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DicionarioPalavra(Base):
    __tablename__ = "dicionario_palavras"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    #: Guardada em minúsculas (``casefold``): ``LACAGEM`` e ``lacagem`` são uma.
    palavra: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    #: Sem chave estrangeira: apagar uma conta não deve levar palavras atrás.
    criado_por_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
