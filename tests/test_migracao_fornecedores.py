"""Migração 96: tabela de fornecedores, semeada a partir do catálogo."""

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
    / "20260825_96_create_fornecedores.py"
)


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_fornecedores", MIGRACAO)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _preparar():
    """A tabela de matérias-primas como está antes desta migração."""
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    tabela = sa.Table(
        "def_materias_primas",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ref_le", sa.String(100)),
        sa.Column("descricao", sa.Text, nullable=False),
        sa.Column("fornecedor", sa.String(150)),
    )
    metadata.create_all(engine)
    return engine, tabela


def _correr(engine, vezes: int = 1) -> None:
    migracao = _carregar_migracao()
    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        for _ in range(vezes):
            migracao.upgrade()


def test_semeia_um_fornecedor_por_nome_distinto_e_liga_as_materias() -> None:
    engine, tabela = _preparar()
    with engine.begin() as connection:
        connection.execute(
            tabela.insert(),
            [
                {"descricao": "Placa A", "fornecedor": "SONAE"},
                {"descricao": "Placa B", "fornecedor": "SONAE"},
                {"descricao": "Ferragem", "fornecedor": " EMUCA "},
                {"descricao": "Sem fornecedor", "fornecedor": None},
                {"descricao": "Fornecedor vazio", "fornecedor": "   "},
            ],
        )

    _correr(engine, vezes=2)  # correr duas vezes não pode duplicar nada

    with engine.begin() as connection:
        nomes = [
            linha[0]
            for linha in connection.execute(
                sa.text("SELECT nome FROM def_fornecedores ORDER BY nome")
            )
        ]
        ligacoes = connection.execute(
            sa.text(
                "SELECT m.descricao, f.nome FROM def_materias_primas m "
                "LEFT JOIN def_fornecedores f ON f.id = m.fornecedor_id "
                "ORDER BY m.id"
            )
        ).all()
    engine.dispose()

    assert nomes == ["EMUCA", "SONAE"]
    assert ligacoes == [
        ("Placa A", "SONAE"),
        ("Placa B", "SONAE"),
        ("Ferragem", "EMUCA"),
        ("Sem fornecedor", None),
        ("Fornecedor vazio", None),
    ]


def test_o_nome_em_texto_fica_como_estava() -> None:
    """A coluna antiga não se perde: é a rede se algum nome não casar."""
    engine, tabela = _preparar()
    with engine.begin() as connection:
        connection.execute(tabela.insert(), [{"descricao": "Placa", "fornecedor": "B&F"}])

    _correr(engine)

    with engine.begin() as connection:
        linha = connection.execute(
            sa.text("SELECT fornecedor, fornecedor_id FROM def_materias_primas")
        ).one()
    engine.dispose()

    assert linha[0] == "B&F"
    assert linha[1] is not None


def test_downgrade_desfaz_tudo() -> None:
    engine, tabela = _preparar()
    with engine.begin() as connection:
        connection.execute(tabela.insert(), [{"descricao": "Placa", "fornecedor": "SONAE"}])

    migracao = _carregar_migracao()
    with engine.begin() as connection:
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.downgrade()

    inspetor = sa.inspect(engine)
    colunas = {c["name"] for c in inspetor.get_columns("def_materias_primas")}
    tabelas = inspetor.get_table_names()
    engine.dispose()

    assert "fornecedor_id" not in colunas
    assert "def_fornecedores" not in tabelas


def test_migracao_encaixa_na_cadeia() -> None:
    migracao = _carregar_migracao()

    assert migracao.revision == "20260825_96"
    assert migracao.down_revision == "20260825_95"
