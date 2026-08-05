"""UserPref SQLAlchemy model: as preferências pessoais de cada utilizador."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserPref(Base):
    """Uma preferência pessoal: o gosto de UM utilizador, não do sistema.

    Existe para separar duas coisas que estavam na mesma tabela: a
    ``system_settings`` guarda o que é da CASA — caminhos do servidor,
    credenciais do PHC/iMos, o interruptor da escrita no iMos — e por isso está
    trancada a só-leitura para quem não é administrador. As escolhas pessoais
    (que validações ver na Preparação, a ordem de impressão, as colunas e as
    vistas da Produção) não têm nada a ver com isso e ficavam reféns dessa
    tranca: um utilizador normal levava ``Error 1142`` ao tentar gravá-las.

    Aqui cada linha pertence a um utilizador e só guarda gosto — por isso pode
    ser escrita por qualquer conta sem abrir mão de nada.
    """

    __tablename__ = "user_prefs"
    __table_args__ = (
        UniqueConstraint("user_id", "chave", name="uq_user_prefs_user_chave"),
        Index("ix_user_prefs_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    #: Sem chave estrangeira de propósito: sem sessão iniciada as preferências
    #: vão para o utilizador 0, e apagar uma conta não deve rebentar aqui.
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    chave: Mapped[str] = mapped_column(String(120), nullable=False)
    valor: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
