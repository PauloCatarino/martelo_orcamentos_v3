"""Tests for the version consumption/cost report service (phase 8W.0)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import OrcamentoItem, OrcamentoVersao
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.relatorio_consumos_service import RelatorioConsumosService


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _criar_versao(session, *, margem_lucro=Decimal("0")) -> int:
    versao = OrcamentoVersao(
        orcamento_id=1, numero_versao=1, codigo_versao="V1", estado="ATIVO",
        margem_lucro_pct=margem_lucro,
    )
    session.add(versao)
    session.flush()
    return versao.id


def _criar_item(session, versao_id, *, ordem, quantidade) -> int:
    item = OrcamentoItem(
        orcamento_versao_id=versao_id, ordem=ordem, tipo_item="OUTRO",
        item=f"Item {ordem}", quantidade=Decimal(quantidade),
    )
    session.add(item)
    session.flush()
    return item.id


def _linha_placa(session, item_id, **kw):
    base = dict(
        orcamento_item_id=item_id, tipo_linha="PECA", descricao="Lateral",
        unidade="m2", quantidade=Decimal("1"), area_m2=Decimal("1"),
        comp_mp=Decimal("2000"), larg_mp=Decimal("1000"), esp_mp=Decimal("19"),
        preco_liquido=Decimal("5"), desperdicio_percentagem=Decimal("0"),
        custo_mp=Decimal("8"), ref_le="LE01", descricao_no_orcamento="AGL",
        nivel=0, ativo=True,
    )
    base.update(kw)
    return OrcamentoItemCusteioLinhaRepository(session).create_linha(**base)


def test_resumo_da_versao_multiplica_por_quantidade_do_item(session) -> None:
    versao_id = _criar_versao(session, margem_lucro=Decimal("10"))
    item_a = _criar_item(session, versao_id, ordem=1, quantidade=2)
    item_b = _criar_item(session, versao_id, ordem=2, quantidade=3)
    _linha_placa(session, item_a)
    _linha_placa(session, item_b)
    session.commit()

    resumo = RelatorioConsumosService(session).resumo_da_versao(versao_id)

    # One board group (same ref/esp), aggregated across both items by item_qt.
    (placa,) = resumo.placas
    assert placa.m2_total_pecas == Decimal("5")     # 1x1x2 + 1x1x3
    assert placa.custo_mp_total == Decimal("40")    # 8x2 + 8x3
    assert placa.area_placa == Decimal("2")         # 2.0 x 1.0
    assert placa.qt_placas == 3                      # ceil(5 / 2)
    assert placa.custo_placa_inteira == Decimal("30")  # 3 x 2 x 5

    # Distribution: produced cost 40, +10% profit -> sell 44, margins 4.
    dist = resumo.distribuicao
    por_nome = {c.nome: c.euros for c in dist.categorias}
    assert por_nome["Placas"] == Decimal("40")
    assert dist.custo_produzido == Decimal("40")
    assert dist.total_venda == Decimal("44")
    assert dist.margens_euros == Decimal("4")


def test_resumo_ignora_linhas_inativas(session) -> None:
    versao_id = _criar_versao(session)
    item = _criar_item(session, versao_id, ordem=1, quantidade=1)
    _linha_placa(session, item)
    _linha_placa(session, item, ativo=False, custo_mp=Decimal("999"))
    session.commit()

    resumo = RelatorioConsumosService(session).resumo_da_versao(versao_id)

    (placa,) = resumo.placas
    assert placa.custo_mp_total == Decimal("8")  # only the active line


def test_resumo_versao_sem_linhas(session) -> None:
    versao_id = _criar_versao(session)
    _criar_item(session, versao_id, ordem=1, quantidade=1)
    session.commit()

    resumo = RelatorioConsumosService(session).resumo_da_versao(versao_id)

    assert resumo.placas == []
    assert resumo.orlas == []
    assert resumo.ferragens == []
    assert resumo.distribuicao.custo_produzido == Decimal("0")
    # The four machine centres always exist (with zero cost).
    assert len(resumo.maquinas) == 4
