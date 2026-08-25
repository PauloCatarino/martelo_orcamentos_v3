"""Migração 95: campos novos das matérias-primas e histórico de preços."""

from __future__ import annotations

import importlib.util
from decimal import Decimal
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
import sqlalchemy as sa

MIGRACAO = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260825_95_materias_primas_no_v3.py"
)

COLUNAS_NOVAS = (
    "data_ultimo_preco",
    "tipo_preco",
    "stock",
    "cor",
    "nome_fabricante",
    "ref_phc",
    "criado_por_id",
    "alterado_por_id",
)


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_mp_no_v3", MIGRACAO)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _tabela_antiga(metadata: sa.MetaData) -> sa.Table:
    """A tabela como estava antes desta migração, com o que interessa ao teste."""
    return sa.Table(
        "def_materias_primas",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ref_le", sa.String(100)),
        sa.Column("descricao", sa.Text, nullable=False),
        sa.Column("desconto", sa.Numeric(8, 4)),
        sa.Column("margem", sa.Numeric(8, 4)),
        sa.Column("desperdicio_percentagem", sa.Numeric(8, 4)),
    )


def _preparar():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    tabela = _tabela_antiga(metadata)
    metadata.create_all(engine)
    return engine, tabela


def test_migracao_cria_colunas_e_historico_e_e_idempotente() -> None:
    engine, _ = _preparar()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.upgrade()  # correr duas vezes não pode partir nada

    # Tudo perguntado antes do dispose: com SQLite em memória, uma ligação nova
    # abre uma base nova e vazia.
    inspetor = sa.inspect(engine)
    colunas = {c["name"] for c in inspetor.get_columns("def_materias_primas")}
    tabelas = inspetor.get_table_names()
    engine.dispose()

    assert set(COLUNAS_NOVAS).issubset(colunas)
    assert "def_materias_primas_precos_historico" in tabelas


def test_migracao_passa_percentagens_de_fracao_para_percentagem_humana() -> None:
    engine, tabela = _preparar()
    with engine.begin() as connection:
        connection.execute(
            tabela.insert(),
            [
                # Vindas do Excel, em fracção.
                {"descricao": "Placa", "desconto": Decimal("0.2"),
                 "margem": None, "desperdicio_percentagem": Decimal("0.15")},
                # Já em percentagem humana: fica como está.
                {"descricao": "Ferragem", "desconto": Decimal("5"),
                 "margem": Decimal("10"), "desperdicio_percentagem": None},
                # Zero e vazio não se tocam.
                {"descricao": "Sem nada", "desconto": Decimal("0"),
                 "margem": None, "desperdicio_percentagem": None},
            ],
        )

    migracao = _carregar_migracao()
    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.upgrade()  # a conversão não pode voltar a multiplicar
        linhas = connection.execute(
            sa.select(tabela).order_by(tabela.c.id)
        ).mappings().all()

    engine.dispose()

    assert float(linhas[0]["desconto"]) == 20
    assert float(linhas[0]["desperdicio_percentagem"]) == 15
    assert float(linhas[1]["desconto"]) == 5
    assert float(linhas[1]["margem"]) == 10
    assert float(linhas[2]["desconto"]) == 0
    assert linhas[2]["margem"] is None


def test_downgrade_devolve_a_tabela_ao_estado_anterior() -> None:
    engine, _ = _preparar()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.downgrade()

    inspetor = sa.inspect(engine)
    colunas = {c["name"] for c in inspetor.get_columns("def_materias_primas")}
    tabelas = inspetor.get_table_names()
    engine.dispose()

    assert not set(COLUNAS_NOVAS) & colunas
    assert "def_materias_primas_precos_historico" not in tabelas


def test_migracao_encaixa_na_cadeia() -> None:
    migracao = _carregar_migracao()

    assert migracao.revision == "20260825_95"
    assert migracao.down_revision == "20260824_94"
