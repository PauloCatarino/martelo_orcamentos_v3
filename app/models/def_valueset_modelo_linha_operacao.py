"""DefValuesetModeloLinhaOperacao SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.operacao_acao_types import ADICIONAR

if TYPE_CHECKING:
    from app.models.def_operacao import DefOperacao
    from app.models.def_valueset_modelo_linha import DefValuesetModeloLinha


class DefValuesetModeloLinhaOperacao(Base):
    """Operation associated with one reusable ValueSet model line."""

    __tablename__ = "def_valueset_modelo_linha_operacoes"
    __table_args__ = (
        UniqueConstraint(
            "def_valueset_modelo_linha_id",
            "def_operacao_id",
            name="uq_def_valueset_modelo_linha_operacoes_linha_operacao",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    def_valueset_modelo_linha_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("def_valueset_modelo_linhas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    def_operacao_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("def_operacoes.id"),
        nullable=False,
        index=True,
    )
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    acao: Mapped[str] = mapped_column(
        String(30), nullable=False, default=ADICIONAR, server_default=ADICIONAR
    )
    regra_calculo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    quantidade_base: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    rasgo_qt_comp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    rasgo_qt_larg: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    tempo_setup_minutos: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    tempo_por_unidade_minutos: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    unidade_tempo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    obrigatorio: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1"
    )
    ativo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="1", index=True
    )
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def_valueset_modelo_linha: Mapped["DefValuesetModeloLinha"] = relationship(
        "DefValuesetModeloLinha",
        back_populates="operacoes",
        foreign_keys=[def_valueset_modelo_linha_id],
    )
    def_operacao: Mapped["DefOperacao"] = relationship(
        "DefOperacao",
        foreign_keys=[def_operacao_id],
    )
