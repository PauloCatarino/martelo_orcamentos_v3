"""OrcamentoItemCusteioLinha SQLAlchemy model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
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
    __table_args__ = (
        CheckConstraint("qt_mod IS NULL OR qt_mod > 0", name="ck_oicl_qt_mod_pos"),
        CheckConstraint("qt_und IS NULL OR qt_und >= 0", name="ck_oicl_qt_und_nonneg"),
        CheckConstraint("quantidade >= 0", name="ck_oicl_quantidade_nonneg"),
        CheckConstraint(
            "comp_real IS NULL OR comp_real > 0", name="ck_oicl_comp_real_pos"
        ),
        CheckConstraint(
            "larg_real IS NULL OR larg_real > 0", name="ck_oicl_larg_real_pos"
        ),
        CheckConstraint(
            "esp_real IS NULL OR esp_real > 0", name="ck_oicl_esp_real_pos"
        ),
        CheckConstraint(
            "preco_liquido IS NULL OR preco_liquido >= 0",
            name="ck_oicl_preco_liquido_nonneg",
        ),
        CheckConstraint(
            "desperdicio_percentagem IS NULL OR desperdicio_percentagem >= 0",
            name="ck_oicl_desperdicio_nonneg",
        ),
        CheckConstraint(
            "comp_mp IS NULL OR comp_mp >= 0", name="ck_oicl_comp_mp_nonneg"
        ),
        CheckConstraint(
            "larg_mp IS NULL OR larg_mp >= 0", name="ck_oicl_larg_mp_nonneg"
        ),
        CheckConstraint("esp_mp IS NULL OR esp_mp >= 0", name="ck_oicl_esp_mp_nonneg"),
        CheckConstraint(
            "acabamento_sup_preco_liquido IS NULL OR "
            "acabamento_sup_preco_liquido >= 0",
            name="ck_oicl_acab_sup_preco_nonneg",
        ),
        CheckConstraint(
            "acabamento_inf_preco_liquido IS NULL OR "
            "acabamento_inf_preco_liquido >= 0",
            name="ck_oicl_acab_inf_preco_nonneg",
        ),
        CheckConstraint(
            "acabamento_sup_desperdicio_percentagem IS NULL OR "
            "acabamento_sup_desperdicio_percentagem >= 0",
            name="ck_oicl_acab_sup_desp_nonneg",
        ),
        CheckConstraint(
            "acabamento_inf_desperdicio_percentagem IS NULL OR "
            "acabamento_inf_desperdicio_percentagem >= 0",
            name="ck_oicl_acab_inf_desp_nonneg",
        ),
    )

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
    # Global display order (phase 8V.3): distinct from the composite-local
    # ``ordem``; set when a separator is spliced in. NULL keeps id order.
    ordem_visual: Mapped[int | None] = mapped_column(Integer, nullable=True)
    origem_tipo: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    origem_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Frozen association/rule snapshot. Catalog changes do not alter an existing
    # quote until an explicit refresh workflow is requested.
    associado_regra_codigo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    associado_regra_expressao: Mapped[str | None] = mapped_column(Text, nullable=True)
    associado_modo_quantidade: Mapped[str | None] = mapped_column(String(30), nullable=True)
    associado_zona_aplicacao: Mapped[str | None] = mapped_column(String(30), nullable=True)
    associado_dimensao_referencia: Mapped[str | None] = mapped_column(String(30), nullable=True)
    associado_numero_topos: Mapped[int | None] = mapped_column(Integer, nullable=True)
    associado_valueset_prioridade: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    operacoes_snapshot_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    tipo_linha: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    codigo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    # Free-text note (phase 8V.1): informative only, never used in calculations
    # and kept separate from the piece's own ``descricao``.
    descricao_livre: Mapped[str | None] = mapped_column(String(255), nullable=True)

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
    # Exact rank of the ValueSet option currently applied to this line.
    valueset_prioridade: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Path of the source module's image, stored on the FIRST line of an imported
    # block so the costing table can show a thumbnail / zoom tooltip (phase 8U.4).
    modulo_imagem_path: Mapped[str | None] = mapped_column(String(500), nullable=True)

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
    # Original (material) waste % saved before a whole-board (Não-Stock) adjustment
    # overwrites ``desperdicio_percentagem`` with the global %, so it can be
    # restored when the board stops being Não-Stock (phase 8W.2.1). NULL = the line
    # is NOT under a whole-board adjustment.
    desperdicio_percentagem_original: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    tipo_materia_prima: Mapped[str | None] = mapped_column(String(100), nullable=True)
    familia_materia_prima: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coresp_orla_0_4: Mapped[str | None] = mapped_column(String(100), nullable=True)
    coresp_orla_1_0: Mapped[str | None] = mapped_column(String(100), nullable=True)
    preco_orla_0_4_m2: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    preco_orla_1_0_m2: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
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
    custo_mp: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_ferragem: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_acabamento: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    # Production costs from machine STD tariffs (phase 8S.1). custo_producao is the
    # sum of the partials (corte + orlagem); NULL when none was computed.
    custo_corte: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_orlagem: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_cnc: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_montagem_manual: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    custo_producao: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    consumo_ml_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    consumo_ml_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    acabamento_face_sup: Mapped[str | None] = mapped_column(String(100), nullable=True)
    acabamento_face_inf: Mapped[str | None] = mapped_column(String(100), nullable=True)
    area_acabamento_sup: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    area_acabamento_inf: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    # Local finishing edits: when True the line's own finishing price/waste
    # prevail over the item ValueSet (the code stays in acabamento_face_sup/inf).
    acabamento_editado_localmente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    acabamento_sup_ref_le: Mapped[str | None] = mapped_column(String(100), nullable=True)
    acabamento_sup_descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acabamento_sup_unidade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    acabamento_sup_preco_liquido: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    acabamento_sup_desperdicio_percentagem: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )
    acabamento_inf_ref_le: Mapped[str | None] = mapped_column(String(100), nullable=True)
    acabamento_inf_descricao: Mapped[str | None] = mapped_column(String(255), nullable=True)
    acabamento_inf_unidade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    acabamento_inf_preco_liquido: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    acabamento_inf_desperdicio_percentagem: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 4), nullable=True
    )

    custo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    custo_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    margem_percentagem: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    preco_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    preco_total: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    # Cost-exclusion flags: True (checked) -> the matching cost is NOT summed
    # into custo_total. Default False -> the cost is included.
    excluir_mp: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    excluir_orla: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    excluir_ferragem: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    excluir_producao: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    excluir_acabamento: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    excluir_mo: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

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
    # Minutes per unit of an OPERACAO_MANUAL line: tempo_manual = minutos_unitarios
    # × QT total, so editing the quantity recomputes time and cost (phase 8S.3).
    minutos_unitarios: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    # Basic production times in MINUTES (decimal), derived from the operations.
    tempo_corte: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    tempo_orlagem: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    tempo_cnc: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    tempo_montagem: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    tempo_setup: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)

    # Production operations mapped from the piece definition (text list, e.g.
    # "CORTE; ORLAGEM; CNC"); no times/costs are computed in this phase.
    operacoes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    maquina: Mapped[str | None] = mapped_column(String(255), nullable=True)
    tipo_producao: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Optional manual factor applied ONLY to custo_producao (empty = 1.00); a fine
    # adjustment per line, e.g. 0.90 (phase 8S.4).
    fator_serie: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)

    override_manual: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    editado_localmente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    material_editado_localmente: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    # Snapshot of DefPeca.sem_material: a service-piece line costs only its
    # operations (no raw material / ValueSet), so the costing skips the material
    # and ValueSet warnings for it (phase 8S.3 follow-up).
    sem_material: Mapped[bool] = mapped_column(
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
