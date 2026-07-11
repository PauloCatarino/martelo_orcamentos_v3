"""DefPeca SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.orla_types import SEM_ORLA
from app.domain.peca_types import SIMPLES
from app.domain.peca_natureza_types import MATERIAL, NEUTRA

if TYPE_CHECKING:
    from app.models.def_peca_componente import DefPecaComponente
    from app.models.def_peca_operacao import DefPecaOperacao


class DefPeca(Base):
    """Reusable piece definition from the technical catalog."""

    __tablename__ = "def_pecas"
    __table_args__ = (
        UniqueConstraint("codigo", name="uq_def_pecas_codigo"),
        Index("ix_def_pecas_nome", "nome"),
        Index("ix_def_pecas_grupo", "grupo"),
        Index("ix_def_pecas_tipo_peca", "tipo_peca"),
        Index("ix_def_pecas_ativo", "ativo"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    codigo: Mapped[str] = mapped_column(String(100), nullable=False)
    nome: Mapped[str] = mapped_column(String(150), nullable=False)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    grupo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tipo_peca: Mapped[str] = mapped_column(String(50), nullable=False, default=SIMPLES, server_default=SIMPLES)
    natureza: Mapped[str] = mapped_column(
        String(30), nullable=False, default=MATERIAL, server_default=MATERIAL, index=True
    )
    orientacao: Mapped[str] = mapped_column(
        String(30), nullable=False, default=NEUTRA, server_default=NEUTRA, index=True
    )
    funcao: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    formula_comp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    formula_larg: Mapped[str | None] = mapped_column(String(100), nullable=True)
    formula_esp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    orla_c1: Mapped[int] = mapped_column(Integer, nullable=False, default=SEM_ORLA, server_default="0")
    orla_c2: Mapped[int] = mapped_column(Integer, nullable=False, default=SEM_ORLA, server_default="0")
    orla_l1: Mapped[int] = mapped_column(Integer, nullable=False, default=SEM_ORLA, server_default="0")
    orla_l2: Mapped[int] = mapped_column(Integer, nullable=False, default=SEM_ORLA, server_default="0")
    chave_valueset_material: Mapped[str | None] = mapped_column(String(100), nullable=True)
    permite_acabamento: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    chave_valueset_acabamento_sup: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chave_valueset_acabamento_inf: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Service piece: consumes no raw material; its cost comes only from the
    # associated operations (cut, CNC, manual, assembly) (phase 8S.3 follow-up).
    sem_material: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    componentes: Mapped[list["DefPecaComponente"]] = relationship(
        "DefPecaComponente",
        back_populates="def_peca_pai",
        foreign_keys="DefPecaComponente.def_peca_pai_id",
    )
    operacoes: Mapped[list["DefPecaOperacao"]] = relationship(
        "DefPecaOperacao",
        back_populates="def_peca",
        foreign_keys="DefPecaOperacao.def_peca_id",
    )
