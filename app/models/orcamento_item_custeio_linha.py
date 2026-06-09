"""OrcamentoItemCusteioLinha SQLAlchemy model."""

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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.def_maquina import DefMaquina
    from app.models.def_materia_prima import DefMateriaPrima
    from app.models.def_operacao import DefOperacao
    from app.models.def_peca import DefPeca
    from app.models.orcamento_item import OrcamentoItem
    from app.models.orcamento_item_modulo import OrcamentoItemModulo


class OrcamentoItemCusteioLinha(Base):
    """One detailed cost line of a budget item."""

    __tablename__ = "orcamento_item_custeio_linhas"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    orcamento_item_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_items.id"),
        nullable=False,
        index=True,
    )
    orcamento_item_modulo_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_item_modulos.id"),
        nullable=True,
        index=True,
    )
    linha_pai_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("orcamento_item_custeio_linhas.id"),
        nullable=True,
        index=True,
    )
    nivel: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    ordem: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origem_tipo: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    origem_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tipo_linha: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    codigo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)

    def_peca_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_pecas.id"),
        nullable=True,
        index=True,
    )
    def_peca_codigo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chave_valueset: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    codigo_orlas: Mapped[str | None] = mapped_column(String(20), nullable=True)
    mat_default: Mapped[str | None] = mapped_column(String(150), nullable=True)

    materia_prima_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_materias_primas.id"),
        nullable=True,
        index=True,
    )
    ref_materia_prima: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descricao_materia_prima: Mapped[str | None] = mapped_column(Text, nullable=True)
    unidade: Mapped[str | None] = mapped_column(String(30), nullable=True)
    ref_le: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descricao_no_orcamento: Mapped[str | None] = mapped_column(Text, nullable=True)
    preco_liquido: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    desperdicio_percentagem: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    tipo_materia_prima: Mapped[str | None] = mapped_column(String(100), nullable=True)
    familia_materia_prima: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coresp_orla_0_4: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coresp_orla_1_0: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comp_mp: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    larg_mp: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    esp_mp: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)

    qt_mod: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    qt_und: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    quantidade: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("1"),
        server_default="1",
    )
    comp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    larg: Mapped[str | None] = mapped_column(String(100), nullable=True)
    esp: Mapped[str | None] = mapped_column(String(100), nullable=True)
    comp_real: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    larg_real: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    esp_real: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    area_m2: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    perimetro_ml: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    ml_orla_fina: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    ml_orla_grossa: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_orla_fina: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_orla_grossa: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_orlas: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    custo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    margem_percentagem: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    preco_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    preco_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    def_operacao_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_operacoes.id"),
        nullable=True,
        index=True,
    )
    def_maquina_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("def_maquinas.id"),
        nullable=True,
        index=True,
    )
    tempo_calculado: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    tempo_manual: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    override_manual: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    editado_localmente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    material_editado_localmente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    origem_material: Mapped[str | None] = mapped_column(String(100), nullable=True)
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

    orcamento_item: Mapped["OrcamentoItem"] = relationship(
        "OrcamentoItem",
        foreign_keys=[orcamento_item_id],
    )
    def_peca: Mapped["DefPeca | None"] = relationship(
        "DefPeca",
        foreign_keys=[def_peca_id],
    )
    orcamento_item_modulo: Mapped["OrcamentoItemModulo | None"] = relationship(
        "OrcamentoItemModulo",
        foreign_keys=[orcamento_item_modulo_id],
    )
    materia_prima: Mapped["DefMateriaPrima | None"] = relationship(
        "DefMateriaPrima",
        foreign_keys=[materia_prima_id],
    )
    def_operacao: Mapped["DefOperacao | None"] = relationship(
        "DefOperacao",
        foreign_keys=[def_operacao_id],
    )
    def_maquina: Mapped["DefMaquina | None"] = relationship(
        "DefMaquina",
        foreign_keys=[def_maquina_id],
    )
