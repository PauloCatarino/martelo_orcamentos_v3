"""Criar persistência do Assistente Lista Material e Centro de PDFs.

Migração exclusivamente aditiva. Não altera ``def_materias_primas`` nem bases
externas (PHC, iMos ou armazém/HOMAG).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260821_91"
down_revision: str | Sequence[str] | None = "20260820_90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    ]


def _create_table(name: str, *columns: sa.SchemaItem) -> None:
    """Criar uma tabela apenas se ainda não existir.

    O MySQL aplica DDL fora de transação. Se uma execução parar a meio, as
    tabelas anteriores ficam criadas; esta proteção permite retomar a migração
    aditiva sem apagar nem recriar dados.
    """
    if not sa.inspect(op.get_bind()).has_table(name):
        op.create_table(name, *columns)


def _create_index(name: str, table: str, columns: list[str]) -> None:
    indexes = {
        item["name"]
        for item in sa.inspect(op.get_bind()).get_indexes(table)
        if item.get("name")
    }
    if name not in indexes:
        op.create_index(name, table, columns)


def upgrade() -> None:
    _create_table(
        "lm_assistente_perfis",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_chave", sa.String(160), nullable=False, server_default=""),
        sa.Column("puxador_default", sa.String(255), nullable=True),
        sa.Column("lacagem_formal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("configuracao_json", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("user_id", "cliente_chave", name="uq_lm_perfil_user_cliente"),
    )
    _create_index("ix_lm_assistente_perfis_user_id", "lm_assistente_perfis", ["user_id"])

    _create_table(
        "lm_assistente_modulos",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_chave", sa.String(160), nullable=False, server_default=""),
        sa.Column("modulo", sa.String(80), nullable=False),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "cliente_chave", "modulo", name="uq_lm_modulo_ambito"),
    )
    _create_index("ix_lm_assistente_modulos_user_id", "lm_assistente_modulos", ["user_id"])

    _create_table(
        "lm_assistente_obras",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("producao_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_chave", sa.String(160), nullable=False, server_default=""),
        sa.Column("workbook_path", sa.String(1024), nullable=True),
        sa.Column("puxador_obra", sa.String(255), nullable=True),
        sa.Column("puxadores_excecoes_json", sa.Text(), nullable=True),
        sa.Column("modulos_json", sa.Text(), nullable=False),
        sa.Column("configuracao_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    _create_index("ix_lm_obra_producao", "lm_assistente_obras", ["producao_id"])

    _create_table(
        "lm_assistente_execucoes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("obra_config_id", sa.BigInteger(), nullable=True),
        sa.Column("producao_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="iniciada"),
        sa.Column("resumo_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("concluida_em", sa.DateTime(), nullable=True),
    )
    _create_index("ix_lm_assistente_execucoes_obra_config_id", "lm_assistente_execucoes", ["obra_config_id"])
    _create_index("ix_lm_assistente_execucoes_producao_id", "lm_assistente_execucoes", ["producao_id"])

    _create_table(
        "lm_assistente_sugestoes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("execucao_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.String(160), nullable=True),
        sa.Column("folha", sa.String(120), nullable=False),
        sa.Column("linha", sa.Integer(), nullable=True),
        sa.Column("campo", sa.String(120), nullable=False),
        sa.Column("original", sa.Text(), nullable=True),
        sa.Column("sugerido", sa.Text(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("confianca", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(30), nullable=False, server_default="pendente"),
        sa.Column("decidido_por_id", sa.BigInteger(), nullable=True),
        sa.Column("decidido_em", sa.DateTime(), nullable=True),
    )
    _create_index("ix_lm_sug_exec_estado", "lm_assistente_sugestoes", ["execucao_id", "estado"])

    _create_table(
        "lm_material_placa_aliases",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("texto_original", sa.String(500), nullable=False),
        sa.Column("texto_normalizado", sa.String(500), nullable=False),
        sa.Column("placa_externa_id", sa.String(160), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cliente_chave", sa.String(160), nullable=False, server_default=""),
        sa.Column("origem", sa.String(40), nullable=False, server_default="historico"),
        sa.Column("estado", sa.String(30), nullable=False, server_default="candidato"),
        sa.Column("confianca", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("suporte", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confirmado_por_id", sa.BigInteger(), nullable=True),
        sa.Column("evidencia_json", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("texto_normalizado", "user_id", "cliente_chave", name="uq_lm_alias_ambito"),
    )
    _create_index("ix_lm_material_placa_aliases_texto_normalizado", "lm_material_placa_aliases", ["texto_normalizado"])
    _create_index("ix_lm_material_placa_aliases_placa_externa_id", "lm_material_placa_aliases", ["placa_externa_id"])

    _create_table(
        "lm_material_orla_relacoes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("material_normalizado", sa.String(255), nullable=False),
        sa.Column("placa_externa_id", sa.String(160), nullable=True),
        sa.Column("orla_normalizada", sa.String(255), nullable=False),
        sa.Column("espessura_orla", sa.Numeric(6, 2), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cliente_chave", sa.String(160), nullable=False, server_default=""),
        sa.Column("origem", sa.String(40), nullable=False),
        sa.Column("estado", sa.String(30), nullable=False, server_default="candidato"),
        sa.Column("confianca", sa.Numeric(5, 4), nullable=False, server_default="0"),
        sa.Column("suporte", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confirmacoes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("rejeicoes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("confirmado_por_id", sa.BigInteger(), nullable=True),
        sa.Column("primeira_utilizacao", sa.DateTime(), nullable=True),
        sa.Column("ultima_utilizacao", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("material_normalizado", "orla_normalizada", "user_id", "cliente_chave", name="uq_lm_orla_ambito"),
    )
    _create_index("ix_lm_orla_material_estado", "lm_material_orla_relacoes", ["material_normalizado", "estado"])

    _create_table(
        "lm_armazem_placas_snapshot",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("external_id", sa.String(160), nullable=False, unique=True),
        sa.Column("codigo_externo", sa.String(255), nullable=True),
        sa.Column("descricao", sa.String(500), nullable=False),
        sa.Column("comprimento", sa.Numeric(12, 3), nullable=True),
        sa.Column("largura", sa.Numeric(12, 3), nullable=True),
        sa.Column("espessura", sa.Numeric(8, 3), nullable=True),
        sa.Column("unidade", sa.String(20), nullable=False, server_default="mm"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("stock", sa.Numeric(14, 3), nullable=True),
        sa.Column("reservado", sa.Numeric(14, 3), nullable=True),
        sa.Column("disponivel", sa.Numeric(14, 3), nullable=True),
        sa.Column("source_hash", sa.String(128), nullable=False),
        sa.Column("synced_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    _create_index("ix_lm_armazem_placas_snapshot_codigo_externo", "lm_armazem_placas_snapshot", ["codigo_externo"])

    _create_table(
        "lm_barra_receitas",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("descricao_normalizada", sa.String(255), nullable=False),
        sa.Column("material_normalizado", sa.String(500), nullable=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("cliente_chave", sa.String(160), nullable=False, server_default=""),
        sa.Column("largura", sa.Numeric(10, 3), nullable=True),
        sa.Column("comprimento", sa.Numeric(12, 3), nullable=True),
        sa.Column("formula", sa.String(255), nullable=True),
        sa.Column("estado", sa.String(30), nullable=False, server_default="candidato"),
        sa.Column("suporte", sa.Integer(), nullable=False, server_default="0"),
    )
    _create_index("ix_lm_barra_receitas_descricao_normalizada", "lm_barra_receitas", ["descricao_normalizada"])

    _create_table(
        "lm_cnc_operacoes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("execucao_id", sa.BigInteger(), nullable=False),
        sa.Column("source_id", sa.String(160), nullable=False),
        sa.Column("lado", sa.String(30), nullable=False),
        sa.Column("operacao", sa.String(80), nullable=False, server_default="CNC_FRESAR"),
        sa.Column("orla_original", sa.String(500), nullable=True),
        sa.Column("orla_resolvida", sa.String(500), nullable=True),
        sa.Column("estado", sa.String(30), nullable=False, server_default="pendente"),
    )
    _create_index("ix_lm_cnc_operacoes_execucao_id", "lm_cnc_operacoes", ["execucao_id"])

    _create_table(
        "lm_pdf_documentos",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("identificador", sa.String(100), nullable=False, unique=True),
        sa.Column("nome", sa.String(255), nullable=False),
        sa.Column("categoria", sa.String(100), nullable=False),
        sa.Column("origem_tipo", sa.String(30), nullable=False),
        sa.Column("origem_valor", sa.String(255), nullable=False),
        sa.Column("nome_ficheiro", sa.String(255), nullable=False),
        sa.Column("combinavel", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ordem", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("ativo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("prerequisitos_json", sa.Text(), nullable=True),
    )

    _create_table(
        "lm_pdf_presets",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("cliente_chave", sa.String(160), nullable=False, server_default=""),
        sa.Column("nome", sa.String(160), nullable=False),
        sa.Column("documentos_json", sa.Text(), nullable=False),
        sa.Column("exportar_separados", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("criar_pacote", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ultimo_usado", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "cliente_chave", "nome", name="uq_lm_pdf_preset"),
    )
    _create_index("ix_lm_pdf_presets_user_id", "lm_pdf_presets", ["user_id"])

    _create_table(
        "lm_pdf_exportacoes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("producao_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("workbook_path", sa.String(1024), nullable=False),
        sa.Column("destino", sa.String(1024), nullable=False),
        sa.Column("documentos_json", sa.Text(), nullable=False),
        sa.Column("resultado_json", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(30), nullable=False, server_default="iniciada"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("concluida_em", sa.DateTime(), nullable=True),
    )
    _create_index("ix_lm_pdf_exportacoes_producao_id", "lm_pdf_exportacoes", ["producao_id"])


def downgrade() -> None:
    # Migração aditiva: o histórico de decisões e exportações não deve ser
    # removido automaticamente por um downgrade.
    pass
