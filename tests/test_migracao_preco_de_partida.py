"""Migração 100: histórico de partida das matérias-primas sem histórico nenhum."""

from __future__ import annotations

import importlib.util
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

MIGRACAO = (
    Path(__file__).resolve().parents[1]
    / "alembic"
    / "versions"
    / "20260901_100_preco_de_partida_materias_primas.py"
)


def _carregar_migracao():
    spec = importlib.util.spec_from_file_location("migracao_preco_partida", MIGRACAO)
    assert spec is not None and spec.loader is not None
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _preparar():
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    materiais = sa.Table(
        "def_materias_primas",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("ref_le", sa.String(100)),
        sa.Column("descricao", sa.Text, nullable=False),
        sa.Column("preco_tabela", sa.Numeric(14, 4)),
        sa.Column("desconto", sa.Numeric(8, 4)),
        sa.Column("margem", sa.Numeric(8, 4)),
        sa.Column("preco_liquido", sa.Numeric(14, 4)),
        sa.Column("data_ultimo_preco", sa.Date),
        sa.Column("origem_dados", sa.String(20)),
        sa.Column("created_at", sa.DateTime),
    )
    historico = sa.Table(
        "def_materias_primas_precos_historico",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("materia_prima_id", sa.Integer, nullable=False),
        sa.Column("ref_le", sa.String(100)),
        sa.Column("preco_tabela", sa.Numeric(14, 4)),
        sa.Column("desconto", sa.Numeric(8, 4)),
        sa.Column("margem", sa.Numeric(8, 4)),
        sa.Column("preco_liquido", sa.Numeric(14, 4)),
        sa.Column("data_preco", sa.Date),
        sa.Column("origem", sa.String(30)),
        sa.Column("user_id", sa.Integer),
        sa.Column("observacoes", sa.Text),
        sa.Column("created_at", sa.DateTime),
    )
    metadata.create_all(engine)
    return engine, materiais, historico


CRIADO = datetime(2026, 6, 5, 23, 3, 52)


def _semear(connection, materiais, historico) -> None:
    connection.execute(
        materiais.insert(),
        [
            # 1 — veio do Excel, com preço e sem histórico: ganha linha de partida.
            {"ref_le": "PLC0055", "descricao": "AGL MATE", "preco_tabela": Decimal("23.46"),
             "margem": Decimal("10"), "preco_liquido": Decimal("25.81"),
             "data_ultimo_preco": date(2025, 7, 23), "origem_dados": "EXCEL",
             "created_at": CRIADO},
            # 2 — origem "V3" não é uma origem de preço válida: conta como MANUAL.
            {"ref_le": "PLC0121", "descricao": "AGL ASM", "preco_tabela": Decimal("8.04"),
             "margem": None, "preco_liquido": Decimal("8.84"),
             "data_ultimo_preco": date(2026, 4, 23), "origem_dados": "V3",
             "created_at": CRIADO},
            # 3 — sem preço nenhum: não se inventa histórico.
            {"ref_le": "FER0001", "descricao": "Dobradiça", "preco_tabela": None,
             "margem": None, "preco_liquido": None, "data_ultimo_preco": None,
             "origem_dados": "EXCEL", "created_at": CRIADO},
            # 4 — já tem histórico: não se mexe.
            {"ref_le": "PLC0051", "descricao": "AGL BRILHO", "preco_tabela": Decimal("21.36"),
             "margem": Decimal("10"), "preco_liquido": Decimal("23.50"),
             "data_ultimo_preco": date(2026, 8, 31), "origem_dados": "V3",
             "created_at": CRIADO},
        ],
    )
    connection.execute(
        historico.insert(),
        [{"materia_prima_id": 4, "ref_le": "PLC0051",
          "preco_tabela": Decimal("21.36"), "preco_liquido": Decimal("23.50"),
          "data_preco": date(2026, 8, 31), "origem": "MANUAL", "user_id": 4,
          "observacoes": None, "created_at": datetime(2026, 8, 31, 12, 18, 55)}],
    )


def test_migracao_escreve_o_preco_de_partida_e_e_idempotente() -> None:
    engine, materiais, historico = _preparar()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        _semear(connection, materiais, historico)
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.upgrade()  # correr duas vezes não pode duplicar nada
        linhas = connection.execute(
            sa.select(historico).order_by(historico.c.materia_prima_id, historico.c.id)
        ).mappings().all()

    engine.dispose()

    por_material = {}
    for linha in linhas:
        por_material.setdefault(linha["materia_prima_id"], []).append(linha)

    # O do Excel ganhou a sua linha de partida, com a data do preço da ficha.
    (partida,) = por_material[1]
    assert partida["ref_le"] == "PLC0055"
    assert partida["preco_tabela"] == Decimal("23.46")
    assert partida["preco_liquido"] == Decimal("25.81")
    assert partida["data_preco"] == date(2025, 7, 23)
    assert partida["origem"] == "EXCEL"
    assert partida["user_id"] is None
    assert partida["created_at"] == CRIADO  # nasce com a idade do material

    # "V3" não é uma origem de preço: fica MANUAL.
    (outro,) = por_material[2]
    assert outro["origem"] == "MANUAL"

    # Sem preço não se inventa histórico.
    assert 3 not in por_material

    # Quem já tinha histórico fica exatamente como estava.
    assert len(por_material[4]) == 1
    assert por_material[4][0]["user_id"] == 4


def test_downgrade_tira_so_as_linhas_que_esta_migracao_escreveu() -> None:
    engine, materiais, historico = _preparar()
    migracao = _carregar_migracao()

    with engine.begin() as connection:
        _semear(connection, materiais, historico)
        migracao.op = Operations(MigrationContext.configure(connection))
        migracao.upgrade()
        migracao.downgrade()
        restantes = connection.execute(
            sa.select(historico.c.materia_prima_id, historico.c.user_id)
        ).mappings().all()

    engine.dispose()

    # Sobra o histórico verdadeiro, o que já lá estava antes.
    assert [dict(linha) for linha in restantes] == [
        {"materia_prima_id": 4, "user_id": 4}
    ]
