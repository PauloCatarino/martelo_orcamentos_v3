"""DefValuesetModeloLinha SQLAlchemy model."""

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

if TYPE_CHECKING:
    from app.models.def_materia_prima import DefMateriaPrima
    from app.models.def_valueset_modelo import DefValuesetModelo
    from app.models.def_valueset_modelo_linha_operacao import (
        DefValuesetModeloLinhaOperacao,
    )


class DefValuesetModeloLinha(Base):
    """One ValueSet line inside a reusable model."""

    __tablename__ = "def_valueset_modelo_linhas"
    __table_args__ = (
        UniqueConstraint(
            "def_valueset_modelo_id",
            "chave",
            "codigo_opcao",
            name="uq_def_valueset_modelo_linhas_modelo_chave_opcao",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    def_valueset_modelo_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("def_valueset_modelos.id"),
        nullable=False,
        index=True,
    )
    chave: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    codigo_opcao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nome_opcao: Mapped[str | None] = mapped_column(String(150), nullable=True)
    padrao: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    prioridade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    descricao: Mapped[str | None] = mapped_column(String(200), nullable=True)
    materia_prima_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_materias_primas.id"),
        nullable=True,
        index=True,
    )
    ref_materia_prima: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descricao_materia_prima: Mapped[str | None] = mapped_column(Text, nullable=True)
    valor_texto: Mapped[str | None] = mapped_column(Text, nullable=True)
    origem: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ref_le: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descricao_no_orcamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    preco_tabela: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    margem_percentagem: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    desconto_percentagem: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    preco_liquido: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    unidade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    desperdicio_percentagem: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    tipo_materia_prima: Mapped[str | None] = mapped_column(String(100), nullable=True)
    familia_materia_prima: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coresp_orla_0_4: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coresp_orla_1_0: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comp_mp: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    larg_mp: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    esp_mp: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    origem_dados: Mapped[str | None] = mapped_column(String(100), nullable=True)
    editado_localmente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    modelo: Mapped["DefValuesetModelo"] = relationship(
        "DefValuesetModelo",
        back_populates="linhas",
    )
    materia_prima: Mapped["DefMateriaPrima | None"] = relationship(
        "DefMateriaPrima",
        foreign_keys=[materia_prima_id],
    )
    operacoes: Mapped[list["DefValuesetModeloLinhaOperacao"]] = relationship(
        "DefValuesetModeloLinhaOperacao",
        back_populates="def_valueset_modelo_linha",
        cascade="all, delete-orphan",
    )
