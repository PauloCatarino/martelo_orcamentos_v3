"""Migração 117: as pastas das listas de ferragens do iMos em Caminhos do Sistema."""

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
    / "20260929_117_pastas_listas_imos.py"
)


def _carregar():
    spec = importlib.util.spec_from_file_location("migracao_117", MIGRACAO)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_cria_as_duas_pastas_sem_mexer_nas_que_existem() -> None:
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    tabela = sa.Table(
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
    migracao = _carregar()
    with engine.begin() as ligacao:
        # Uma já personalizada: fica como está.
        ligacao.execute(
            tabela.insert().values(
                chave="pasta_listas_imos_rdl", valor=r"J:\Outra", descricao="x", tipo="pasta", grupo="IMOS", ativo=True
            )
        )
        migracao.op = Operations(MigrationContext.configure(ligacao))
        migracao.upgrade()
        migracao.upgrade()
        linhas = {l["chave"]: l for l in ligacao.execute(sa.select(tabela)).mappings().all()}
    engine.dispose()

    assert set(linhas) == {"pasta_listas_imos_rdl", "pasta_motor_relatorios"}
    assert linhas["pasta_listas_imos_rdl"]["valor"] == r"J:\Outra"
    assert linhas["pasta_motor_relatorios"]["valor"] == ""
    assert linhas["pasta_motor_relatorios"]["grupo"] == "IMOS"
    assert migracao.down_revision == "20260924_116"
