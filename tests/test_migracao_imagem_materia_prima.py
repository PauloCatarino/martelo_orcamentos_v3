"""A migração que dá imagem à ficha da matéria-prima.

Duas coisas ao mesmo tempo: a coluna com o nome do ficheiro e a configuração
que diz onde vive a pasta das imagens do iMos.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRACAO = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260903_103_imagem_da_materia_prima.py"
)


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_imagem_materia_prima", MIGRACAO)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _base() -> sa.Engine:
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "def_materias_primas",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ref_le", sa.String(100)),
        sa.Column("descricao", sa.Text, nullable=False),
    )
    sa.Table(
        "system_settings",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("chave", sa.String(100), nullable=False, unique=True),
        sa.Column("valor", sa.Text),
        sa.Column("descricao", sa.Text),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("grupo", sa.String(100)),
        sa.Column("ativo", sa.Boolean, nullable=False),
    )
    metadata.create_all(engine)
    return engine


def _colunas(connection) -> set[str]:
    inspector = sa.inspect(connection)
    return {coluna["name"] for coluna in inspector.get_columns("def_materias_primas")}


def test_acrescenta_coluna_e_configuracao_e_pode_correr_duas_vezes() -> None:
    engine = _base()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        # Correr outra vez não pode rebentar nem duplicar a configuração.
        migracao.upgrade()
        colunas = _colunas(connection)
        linhas = connection.execute(
            sa.text("SELECT chave, valor, tipo, grupo FROM system_settings")
        ).mappings().all()

    engine.dispose()
    assert "imagem_ficheiro" in colunas
    assert len(linhas) == 1
    assert linhas[0]["chave"] == "pasta_imagens_imos"
    assert linhas[0]["valor"] == r"I:\Library\Info\BITMAPS"
    assert linhas[0]["tipo"] == "pasta"
    assert linhas[0]["grupo"] == "IMOS"


def test_nao_pisa_uma_pasta_ja_configurada_a_mao() -> None:
    engine = _base()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO system_settings (chave, valor, descricao, tipo, grupo, ativo) "
                "VALUES ('pasta_imagens_imos', 'X:/outra/pasta', '', 'pasta', 'IMOS', 1)"
            )
        )
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        valor = connection.execute(
            sa.text("SELECT valor FROM system_settings WHERE chave = 'pasta_imagens_imos'")
        ).scalar()

    engine.dispose()
    assert valor == "X:/outra/pasta"


def test_downgrade_tira_a_coluna_e_deixa_a_configuracao() -> None:
    engine = _base()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.downgrade()
        # Sem a coluna, voltar a descer não pode rebentar.
        migracao.downgrade()
        colunas = _colunas(connection)
        quantas = connection.execute(
            sa.text("SELECT COUNT(*) FROM system_settings WHERE chave = 'pasta_imagens_imos'")
        ).scalar()

    engine.dispose()
    assert "imagem_ficheiro" not in colunas
    # O caminho pode ter sido personalizado: não se apaga num downgrade.
    assert quantas == 1
