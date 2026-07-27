"""Occurrence log of one production work (obra) — one ticket per line."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProducaoOcorrencia(Base):
    """One ticket of the obra: quando, quem, o quê — e em que pé está.

    Não é auditoria do que o programa mudou — é o registo do que aconteceu na
    vida real: o que o cliente reportou, o que se combinou, o que correu mal.
    A classificação (``tipo``, ``origem``) existe para se poder avaliar os erros
    por obra no fim do ano; o ``estado`` e o ``responsavel`` para não se perder
    nenhum pedido pelo caminho.
    """

    __tablename__ = "producao_ocorrencias"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    producao_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("producao.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    #: Nome de quem escreveu, guardado à cabeça (sobrevive a contas apagadas).
    autor: Mapped[str | None] = mapped_column(String(255), nullable=True)
    texto: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    #: Número sequencial dentro da obra (T1, T2…). É por isto que as pessoas se
    #: referem ao ticket na conversa, por isso não pode saltar nem repetir.
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assunto: Mapped[str | None] = mapped_column(String(200), nullable=True)

    tipo: Mapped[str | None] = mapped_column(String(40), nullable=True, index=True)
    gravidade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    origem: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estado: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)

    #: Texto livre, alinhado com ``producao.responsavel`` (que também é texto).
    responsavel: Mapped[str | None] = mapped_column(String(100), nullable=True)
    responsavel_membro_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("equipa_membros.id", ondelete="SET NULL"),
        nullable=True,
    )

    custo_estimado: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    resolvido_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolvido_por: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, onupdate=func.now()
    )

    #: Prova de que a pessoa foi avisada — é metade da razão de ser do ticket.
    enviado_em: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    enviado_para: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enviado_via: Mapped[str | None] = mapped_column(String(20), nullable=True)

    anexos = relationship(
        "ProducaoOcorrenciaAnexo",
        back_populates="ocorrencia",
        cascade="all, delete-orphan",
        order_by="ProducaoOcorrenciaAnexo.ordem, ProducaoOcorrenciaAnexo.id",
        lazy="selectin",
    )
