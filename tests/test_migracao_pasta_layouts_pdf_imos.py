"""Data migration for the local folder of iMos layout PDFs."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa


MIGRACAO = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260823_93_add_pasta_layouts_pdf_imos.py"
)


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_layouts_pdf_imos", MIGRACAO)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_migracao_adiciona_configuracao_e_e_idempotente() -> None:
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

    migracao = _carregar_migracao()
    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.upgrade()
        linhas = connection.execute(sa.select(tabela)).mappings().all()

    engine.dispose()
    assert len(linhas) == 1
    assert linhas[0]["chave"] == "pasta_layouts_pdf_imos"
    assert linhas[0]["valor"] == r"C:\IMOS_Output_Batches\PDF_MultiSheet_Layout"
    assert linhas[0]["descricao"] == "Pasta onde vão os PDFs dos Layouts da obra"
    assert linhas[0]["tipo"] == "pasta"
    assert linhas[0]["grupo"] == "IMOS"
    assert linhas[0]["ativo"] is True
