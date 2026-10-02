"""Registo de horas: um dia por pessoa e os envios do mês à contabilidade."""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RegistoHorasDia(Base):
    """Um dia da folha de horas de uma pessoa (uma linha por dia).

    As horas guardam-se em minutos. As contas (trabalhado, normais, extra)
    ficam gravadas tal como saíram no dia em que se guardou: mudar mais tarde
    as horas normais de alguém não reescreve meses que já foram pagos.
    """

    __tablename__ = "registo_horas_dias"
    __table_args__ = (
        UniqueConstraint("user_id", "data", name="uq_registo_horas_dias_user_data"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False, index=True
    )
    data: Mapped[date] = mapped_column(Date, nullable=False)
    #: util | fim_semana | feriado | ferias | folga (ver app.domain.registo_horas).
    tipo: Mapped[str] = mapped_column(String(16), nullable=False)
    #: Minutos desde a meia-noite; a saída pode passar de 1440 (dia seguinte).
    entrada_min: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    saida_min: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    #: 2.º período do dia útil (ex.: em casa, à noite).
    entrada2_min: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    saida2_min: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    desconto_almoco: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    desconto_jantar: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    acerto_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    #: Fora dos dias úteis: horas trabalhadas (na folga, as horas a descontar).
    horas_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    trabalhado_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    normais_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    extra_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=0, server_default="0"
    )
    #: As horas normais do dia que valiam quando se guardou (480 = 8h).
    horas_normais_dia_min: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=480, server_default="480"
    )
    observacoes: Mapped[str] = mapped_column(
        String(255), nullable=False, default="", server_default=""
    )
    #: martelo | app_antiga (histórico importado da app PHP isolada).
    origem: Mapped[str] = mapped_column(
        String(20), nullable=False, default="martelo", server_default="martelo"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RegistoHorasEnvio(Base):
    """Cada envio de um mês à contabilidade (um mês pode ser reenviado)."""

    __tablename__ = "registo_horas_envios"
    __table_args__ = (
        Index("ix_registo_horas_envios_user_mes", "user_id", "ano", "mes"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    ano: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    mes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    enviado_em: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    destinatario: Mapped[str] = mapped_column(String(255), nullable=False)
    normais_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    extra_min: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    dias_registados: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    ficheiro: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=""
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
