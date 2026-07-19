"""CNC costing rework: machine capabilities + method-driven operation links.

DESTRUCTIVE (test phase, approved): renames the CNC machines
(CNC_HORIZONTAL -> CNC_SANDWICH, CNC_5_EIXOS_ORLAGEM -> CNC_5_EIXOS), creates
the coating machine REVESTIMENTO_SANDWICH, replaces the generic CNC catalog
operations (CNC_MECANIZACAO / CNC_RASGO are DELETED) by one operation per CNC
machine, backfills ``metodo_calculo`` on every CNC link and clears the legacy
operation snapshots of costing lines. ``downgrade`` restores the schema only —
the data transformation is not reversible.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260805_75"
down_revision: str | Sequence[str] | None = "20260804_74"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# The 4 catalog/ValueSet association tables that lose the unique constraint
# (the new model allows several method lines of the same operation) plus the
# local costing-line snapshot table (which never had one).
_UCS = (
    (
        "def_peca_operacoes",
        "uq_def_peca_operacoes_peca_operacao",
        "ix_def_peca_operacoes_peca_operacao",
        ("def_peca_id", "def_operacao_id"),
    ),
    (
        "def_valueset_modelo_linha_operacoes",
        "uq_def_valueset_modelo_linha_operacoes_linha_operacao",
        "ix_def_valueset_modelo_linha_ops_linha_operacao",
        ("def_valueset_modelo_linha_id", "def_operacao_id"),
    ),
    (
        "orcamento_valueset_linha_operacoes",
        "uq_orcamento_valueset_linha_operacoes_linha_operacao",
        "ix_orcamento_valueset_linha_ops_linha_operacao",
        ("orcamento_valueset_linha_id", "def_operacao_id"),
    ),
    (
        "orcamento_item_valueset_linha_operacoes",
        "uq_orcamento_item_valueset_linha_operacoes_linha_operacao",
        "ix_orcamento_item_valueset_linha_ops_linha_operacao",
        ("orcamento_item_valueset_linha_id", "def_operacao_id"),
    ),
)

_ASSOC_TABLES = (
    "def_peca_operacoes",
    "def_valueset_modelo_linha_operacoes",
    "orcamento_valueset_linha_operacoes",
    "orcamento_item_valueset_linha_operacoes",
    "orcamento_item_custeio_linha_operacoes",
)

# codigo -> (permite_escaloes_area, permite_furacao, permite_rasgos,
#            permite_pocket, preco_furo_std, preco_furo_serie)
_CAPACIDADES_CNC = {
    "CNC_ABD": (True, True, False, False, "0.10", "0.07"),
    "CNC_VERTICAL": (True, True, True, True, "0.12", "0.09"),
    "CNC_SANDWICH": (True, True, True, False, "0.10", "0.06"),
    "CNC_5_EIXOS": (True, True, True, True, "0.15", "0.11"),
}

_OPERACOES_CNC = (
    ("CNC_ABD", "CNC ABD"),
    ("CNC_VERTICAL", "CNC Vertical"),
    ("CNC_SANDWICH", "CNC Sandwich"),
    ("CNC_5_EIXOS", "CNC 5 Eixos"),
)


def upgrade() -> None:
    _ddl_upgrade()
    _migrar_dados()


def _ddl_upgrade() -> None:
    # Machine capabilities + new tariffs.
    op.add_column(
        "def_maquinas",
        sa.Column("permite_furacao", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "def_maquinas",
        sa.Column("permite_pocket", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.add_column(
        "def_maquinas",
        sa.Column(
            "permite_escaloes_area", sa.Boolean(), nullable=False, server_default="0"
        ),
    )
    for coluna in (
        "preco_furo_std",
        "preco_furo_serie",
        "preco_m2_face_std",
        "preco_m2_face_serie",
    ):
        op.add_column("def_maquinas", sa.Column(coluna, sa.Numeric(14, 4), nullable=True))

    # Method column on every association table.
    for tabela in _ASSOC_TABLES:
        op.add_column(tabela, sa.Column("metodo_calculo", sa.String(30), nullable=True))
        op.create_index(f"ix_{tabela}_metodo_calculo", tabela, ["metodo_calculo"])

    # Unique constraints -> plain composite indexes.
    for tabela, uq, ix, colunas in _UCS:
        op.drop_constraint(uq, tabela, type_="unique")
        op.create_index(ix, tabela, list(colunas))

    # Coating cost bucket on costing lines.
    op.add_column(
        "orcamento_item_custeio_linhas",
        sa.Column("custo_revestimento", sa.Numeric(14, 4), nullable=True),
    )


def _migrar_dados() -> None:
    conn = op.get_bind()

    def scalar(sql: str, **params):
        return conn.execute(sa.text(sql), params).scalar()

    def execute(sql: str, **params) -> None:
        conn.execute(sa.text(sql), params)

    # 1. Machine renames (guarded: skip when the target code already exists).
    for antigo, novo, nome_novo in (
        ("CNC_HORIZONTAL", "CNC_SANDWICH", "CNC Sandwich"),
        ("CNC_5_EIXOS_ORLAGEM", "CNC_5_EIXOS", None),
    ):
        existe_novo = scalar(
            "SELECT COUNT(*) FROM def_maquinas WHERE codigo = :novo", novo=novo
        )
        if existe_novo:
            execute(
                "UPDATE def_maquinas SET ativo = 0 WHERE codigo = :antigo",
                antigo=antigo,
            )
            continue
        if nome_novo is not None:
            execute(
                "UPDATE def_maquinas SET codigo = :novo, nome = :nome "
                "WHERE codigo = :antigo",
                novo=novo,
                nome=nome_novo,
                antigo=antigo,
            )
        else:
            execute(
                "UPDATE def_maquinas SET codigo = :novo WHERE codigo = :antigo",
                novo=novo,
                antigo=antigo,
            )

    # 2. Capability flags + proposed €/furo tariffs on the CNC machines.
    for codigo, (esc, fur, ras, poc, furo_std, furo_serie) in _CAPACIDADES_CNC.items():
        execute(
            "UPDATE def_maquinas SET permite_escaloes_area = :esc, "
            "permite_furacao = :fur, permite_rasgos = :ras, permite_pocket = :poc, "
            "preco_furo_std = COALESCE(preco_furo_std, :furo_std), "
            "preco_furo_serie = COALESCE(preco_furo_serie, :furo_serie) "
            "WHERE codigo = :codigo",
            esc=esc,
            fur=fur,
            ras=ras,
            poc=poc,
            furo_std=furo_std,
            furo_serie=furo_serie,
            codigo=codigo,
        )

    # 3. Coating machine.
    if not scalar(
        "SELECT COUNT(*) FROM def_maquinas WHERE codigo = 'REVESTIMENTO_SANDWICH'"
    ):
        execute(
            "INSERT INTO def_maquinas (codigo, nome, descricao, tipo, "
            "preco_m2_face_std, preco_m2_face_serie, permite_rasgos, "
            "permite_furacao, permite_pocket, permite_escaloes_area, ativo) "
            "VALUES ('REVESTIMENTO_SANDWICH', 'Revestimento Sandwich', "
            "'Reveste paineis sandwich em 1 ou 2 faces; tarifa por m2 e por "
            "face revestida.', 'REVESTIMENTO', 3.25, 3.25, 0, 0, 0, 0, 1)"
        )
    else:
        execute(
            "UPDATE def_maquinas SET tipo = 'REVESTIMENTO', ativo = 1, "
            "preco_m2_face_std = COALESCE(preco_m2_face_std, 3.25), "
            "preco_m2_face_serie = COALESCE(preco_m2_face_serie, 3.25) "
            "WHERE codigo = 'REVESTIMENTO_SANDWICH'"
        )

    # 4. One catalog operation per CNC machine (reuses rows the user created by
    # hand — e.g. CNC_5_EIXOS / CNC_SANDWICH — fixing machine and type).
    for codigo, nome in _OPERACOES_CNC:
        maquina_id = scalar(
            "SELECT id FROM def_maquinas WHERE codigo = :codigo", codigo=codigo
        )
        if maquina_id is None:
            continue
        if scalar(
            "SELECT COUNT(*) FROM def_operacoes WHERE codigo = :codigo", codigo=codigo
        ):
            execute(
                "UPDATE def_operacoes SET nome = :nome, tipo_operacao = 'CNC', "
                "unidade_calculo = 'PECA', maquina_id = :maquina_id, ativo = 1 "
                "WHERE codigo = :codigo",
                nome=nome,
                maquina_id=maquina_id,
                codigo=codigo,
            )
        else:
            execute(
                "INSERT INTO def_operacoes (codigo, nome, tipo_operacao, "
                "unidade_calculo, maquina_id, ativo) VALUES (:codigo, :nome, "
                "'CNC', 'PECA', :maquina_id, 1)",
                codigo=codigo,
                nome=nome,
                maquina_id=maquina_id,
            )

    revestimento_maquina_id = scalar(
        "SELECT id FROM def_maquinas WHERE codigo = 'REVESTIMENTO_SANDWICH'"
    )
    if revestimento_maquina_id is not None and not scalar(
        "SELECT COUNT(*) FROM def_operacoes WHERE codigo = 'REVESTIMENTO_SANDWICH'"
    ):
        execute(
            "INSERT INTO def_operacoes (codigo, nome, tipo_operacao, "
            "unidade_calculo, maquina_id, ativo) VALUES "
            "('REVESTIMENTO_SANDWICH', 'Revestimento Sandwich', 'REVESTIMENTO', "
            "'M2', :maquina_id, 1)",
            maquina_id=revestimento_maquina_id,
        )

    # 5. Repoint links of the deleted generic operations to the CNC_VERTICAL
    # operation (groove links keep their geometry and become metodo RASGO).
    id_vertical = scalar("SELECT id FROM def_operacoes WHERE codigo = 'CNC_VERTICAL'")
    id_mecanizacao = scalar(
        "SELECT id FROM def_operacoes WHERE codigo = 'CNC_MECANIZACAO'"
    )
    id_rasgo = scalar("SELECT id FROM def_operacoes WHERE codigo = 'CNC_RASGO'")
    if id_vertical is not None:
        for tabela in _ASSOC_TABLES:
            if id_mecanizacao is not None:
                execute(
                    f"UPDATE {tabela} SET def_operacao_id = :novo "
                    "WHERE def_operacao_id = :antigo",
                    novo=id_vertical,
                    antigo=id_mecanizacao,
                )
            if id_rasgo is not None:
                execute(
                    f"UPDATE {tabela} SET def_operacao_id = :novo, "
                    "metodo_calculo = 'RASGO' WHERE def_operacao_id = :antigo",
                    novo=id_vertical,
                    antigo=id_rasgo,
                )
        execute(
            "UPDATE orcamento_item_custeio_linha_operacoes "
            "SET codigo = 'CNC_VERTICAL', nome = 'CNC Vertical' "
            "WHERE def_operacao_id = :novo "
            "AND codigo IN ('CNC_MECANIZACAO', 'CNC_RASGO')",
            novo=id_vertical,
        )

    # 6. Backfill metodo_calculo on every CNC link (same heuristic as
    # inferir_metodo_calculo_legado); coating links get REVESTIMENTO.
    caso = (
        "CASE WHEN UPPER(COALESCE({t}.regra_calculo, '')) = 'RASGO_CNC' "
        "OR {t}.rasgo_qt_comp > 0 OR {t}.rasgo_qt_larg > 0 THEN 'RASGO' "
        "WHEN UPPER(COALESCE({t}.regra_calculo, '')) = 'POR_FURACAO' "
        "THEN 'FURACAO' "
        "WHEN {t}.tempo_por_unidade_minutos IS NOT NULL "
        "OR {t}.tempo_setup_minutos IS NOT NULL THEN 'TEMPO' "
        "ELSE 'ESCALAO_AREA' END"
    )
    for tabela in _ASSOC_TABLES:
        execute(
            f"UPDATE {tabela} t JOIN def_operacoes o ON o.id = t.def_operacao_id "
            f"SET t.metodo_calculo = {caso.format(t='t')} "
            "WHERE t.metodo_calculo IS NULL "
            "AND UPPER(COALESCE(o.tipo_operacao, '')) = 'CNC'"
        )
        execute(
            f"UPDATE {tabela} t JOIN def_operacoes o ON o.id = t.def_operacao_id "
            "SET t.metodo_calculo = 'REVESTIMENTO' "
            "WHERE t.metodo_calculo IS NULL "
            "AND UPPER(COALESCE(o.tipo_operacao, '')) = 'REVESTIMENTO'"
        )
    # Local rows may have no def_operacao_id: use their own snapshot type.
    execute(
        "UPDATE orcamento_item_custeio_linha_operacoes t "
        f"SET t.metodo_calculo = {caso.format(t='t')} "
        "WHERE t.metodo_calculo IS NULL AND t.def_operacao_id IS NULL "
        "AND UPPER(COALESCE(t.tipo_operacao, '')) = 'CNC'"
    )

    # 7. Delete the generic CNC operations (their links were repointed above).
    execute(
        "DELETE FROM def_operacoes WHERE codigo IN ('CNC_MECANIZACAO', 'CNC_RASGO')"
    )

    # 8. Invalidate legacy operation snapshots on costing lines: they carry the
    # old operation set; recalculating regenerates them under the new model.
    execute(
        "UPDATE orcamento_item_custeio_linhas SET operacoes_snapshot_json = NULL "
        "WHERE operacoes_snapshot_json IS NOT NULL"
    )


def downgrade() -> None:
    """Schema-only rollback; the data transformation is not restored."""
    op.drop_column("orcamento_item_custeio_linhas", "custo_revestimento")

    for tabela, uq, ix, colunas in _UCS:
        op.drop_index(ix, table_name=tabela)
        op.create_unique_constraint(uq, tabela, list(colunas))

    for tabela in _ASSOC_TABLES:
        op.drop_index(f"ix_{tabela}_metodo_calculo", table_name=tabela)
        op.drop_column(tabela, "metodo_calculo")

    for coluna in (
        "preco_m2_face_serie",
        "preco_m2_face_std",
        "preco_furo_serie",
        "preco_furo_std",
        "permite_escaloes_area",
        "permite_pocket",
        "permite_furacao",
    ):
        op.drop_column("def_maquinas", coluna)
