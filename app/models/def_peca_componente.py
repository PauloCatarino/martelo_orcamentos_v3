"""DefPecaComponente SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.componente_types import PECA
from app.domain.associado_types import COMP, GERAL, TOTAL

if TYPE_CHECKING:
    from app.models.def_peca import DefPeca
    from app.models.def_regra_quantidade import DefRegraQuantidade


class DefPecaComponente(Base):
    """Component associated with one composite piece definition."""

    __tablename__ = "def_peca_componentes"
    __table_args__ = (
        UniqueConstraint("def_peca_pai_id", "ordem", name="uq_def_peca_componentes_pai_ordem"),
        CheckConstraint(
            "prioridade_valueset >= 1",
            name="ck_def_peca_componentes_prioridade_valueset_pos",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    def_peca_pai_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("def_pecas.id"),
        nullable=False,
        index=True,
    )
    tipo_componente: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default=PECA,
        server_default=PECA,
        index=True,
    )
    def_peca_componente_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_pecas.id"),
        nullable=True,
        index=True,
    )
    referencia_componente: Mapped[str | None] = mapped_column(String(150), nullable=True)
    descricao: Mapped[str | None] = mapped_column(Text, nullable=True)
    formula_comp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    formula_larg: Mapped[str | None] = mapped_column(String(100), nullable=True)
    formula_esp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(12, 3),
        nullable=False,
        default=Decimal("1"),
        server_default="1",
    )
    regra_quantidade: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default="FIXA",
        server_default="FIXA",
    )
    # Optional configurable quantity rule (phase 8T.5.1). When set, the
    # component quantity is computed by this rule from the main piece dimensions;
    # the fixed quantidade / regra_quantidade above are the fallback.
    def_regra_quantidade_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_regras_quantidade.id"),
        nullable=True,
        index=True,
    )
    zona_aplicacao: Mapped[str] = mapped_column(
        String(30), nullable=False, default=GERAL, server_default=GERAL, index=True
    )
    dimensao_referencia: Mapped[str] = mapped_column(
        String(30), nullable=False, default=COMP, server_default=COMP
    )
    numero_topos: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    modo_quantidade: Mapped[str] = mapped_column(
        String(30), nullable=False, default=TOTAL, server_default=TOTAL
    )
    # Exact rank of the item ValueSet option used by this association. This
    # allows two associations with the same component/key to resolve different
    # materials (for example, priority 1 = dowel, priority 2 = screw).
    prioridade_valueset: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    obrigatorio: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1", index=True)
    observacoes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    def_peca_pai: Mapped["DefPeca"] = relationship(
        "DefPeca",
        back_populates="componentes",
        foreign_keys=[def_peca_pai_id],
    )
    def_peca_componente: Mapped["DefPeca | None"] = relationship(
        "DefPeca",
        foreign_keys=[def_peca_componente_id],
    )
    def_regra_quantidade: Mapped["DefRegraQuantidade | None"] = relationship(
        "DefRegraQuantidade",
        foreign_keys=[def_regra_quantidade_id],
    )
