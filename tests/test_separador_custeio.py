"""Tests for the visual separator cost line (phase 8V.3)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import OrcamentoItem, OrcamentoItemValuesetLinha
from app.repositories.def_peca_repository import DefPecaRepository
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


@compiles(BigInteger, "sqlite")
def _bigint_as_integer_on_sqlite(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _criar_item(session) -> int:
    item = OrcamentoItem(
        orcamento_versao_id=1, ordem=1, tipo_item="OUTRO", item="Item",
        quantidade=Decimal("1"), altura=Decimal("2000"),
        largura=Decimal("1000"), profundidade=Decimal("500"),
    )
    session.add(item)
    session.flush()
    return item.id


def _criar_linha(session, item_id, **fields):
    base = dict(
        orcamento_item_id=item_id, tipo_linha="PECA", descricao="Linha",
        quantidade=Decimal("1"), nivel=0, ativo=True,
    )
    base.update(fields)
    linha = OrcamentoItemCusteioLinhaRepository(session).create_linha(**base)
    session.commit()
    return linha


def _tipos(session, item_id):
    return [
        l.tipo_linha
        for l in OrcamentoItemCusteioLinhaRepository(session)
        .list_active_by_orcamento_item(item_id)
    ]


def test_inserir_separador_abaixo_da_linha_reordena(session) -> None:
    item_id = _criar_item(session)
    a = _criar_linha(session, item_id, descricao="A")
    b = _criar_linha(session, item_id, descricao="B")
    c = _criar_linha(session, item_id, descricao="C")
    service = OrcamentoItemCusteioLinhaService(session)

    sep = service.inserir_separador(item_id, b.id)
    assert sep.tipo_linha == "SEPARADOR"

    # The separator lands right BELOW B, keeping A ... B, SEP, C.
    linhas = OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        item_id
    )
    ids = [l.id for l in linhas]
    assert ids == [a.id, b.id, sep.id, c.id]


def _criar_composta(session, item_id):
    """A composite block: header + two children, between simple pieces A and B."""
    a = _criar_linha(session, item_id, descricao="A")
    header = _criar_linha(
        session, item_id, tipo_linha="PECA_COMPOSTA", def_peca_id=5,
        def_peca_codigo="GAVETA", descricao="Gaveta",
    )
    filho1 = _criar_linha(
        session, item_id, tipo_linha="FERRAGEM", descricao="Corrediça",
        nivel=1, linha_pai_id=header.id,
    )
    filho2 = _criar_linha(
        session, item_id, tipo_linha="PECA", descricao="Fundo",
        nivel=1, linha_pai_id=header.id,
    )
    b = _criar_linha(session, item_id, descricao="B")
    return a, header, filho1, filho2, b


def test_separador_no_cabecalho_da_composta_vai_apos_o_bloco(session) -> None:
    item_id = _criar_item(session)
    a, header, filho1, filho2, b = _criar_composta(session, item_id)
    service = OrcamentoItemCusteioLinhaService(session)

    # Selecting the composite header: the separator must go AFTER the last child.
    sep = service.inserir_separador(item_id, header.id)

    ids = [l.id for l in OrcamentoItemCusteioLinhaRepository(session)
           .list_active_by_orcamento_item(item_id)]
    assert ids == [a.id, header.id, filho1.id, filho2.id, sep.id, b.id]


def test_separador_num_filho_da_composta_vai_apos_o_bloco(session) -> None:
    item_id = _criar_item(session)
    a, header, filho1, filho2, b = _criar_composta(session, item_id)
    service = OrcamentoItemCusteioLinhaService(session)

    # Selecting a child: still after the whole block, never between children.
    sep = service.inserir_separador(item_id, filho1.id)

    ids = [l.id for l in OrcamentoItemCusteioLinhaRepository(session)
           .list_active_by_orcamento_item(item_id)]
    assert ids == [a.id, header.id, filho1.id, filho2.id, sep.id, b.id]


def test_separador_em_peca_simples_fica_abaixo(session) -> None:
    item_id = _criar_item(session)
    a, header, filho1, filho2, b = _criar_composta(session, item_id)
    service = OrcamentoItemCusteioLinhaService(session)

    # A simple piece (A): the separator goes right below it (no block protection).
    sep = service.inserir_separador(item_id, a.id)

    ids = [l.id for l in OrcamentoItemCusteioLinhaRepository(session)
           .list_active_by_orcamento_item(item_id)]
    assert ids == [a.id, sep.id, header.id, filho1.id, filho2.id, b.id]


def test_inserir_separador_sem_selecao_vai_para_o_fim(session) -> None:
    item_id = _criar_item(session)
    a = _criar_linha(session, item_id, descricao="A")
    b = _criar_linha(session, item_id, descricao="B")
    service = OrcamentoItemCusteioLinhaService(session)

    sep = service.inserir_separador(item_id, None)

    ids = [l.id for l in OrcamentoItemCusteioLinhaRepository(session)
           .list_active_by_orcamento_item(item_id)]
    assert ids == [a.id, b.id, sep.id]


def test_separador_e_ignorado_pelos_recalculos(session) -> None:
    item_id = _criar_item(session)
    # A real costable piece (M2 material) + a separator below it.
    linha_vs = OrcamentoItemValuesetLinha(
        orcamento_item_id=item_id, chave="MATERIAL_LATERAIS", padrao=True, ordem=1,
        preco_liquido=Decimal("5.79"), unidade="m2",
        desperdicio_percentagem=Decimal("5"),
    )
    session.add(linha_vs)
    peca = _criar_linha(
        session, item_id, tipo_linha="PECA", descricao="Lateral",
        comp="H", larg="P", chave_valueset="MATERIAL_LATERAIS",
        unidade="m2", preco_liquido=Decimal("5.79"),
        desperdicio_percentagem=Decimal("5"), qt_und=Decimal("1"),
    )
    session.commit()
    service = OrcamentoItemCusteioLinhaService(session)
    sep = service.inserir_separador(item_id, peca.id)

    # Run measure + material + total steps of the pipeline.
    service.recalcular_medidas_do_item(item_id)
    service.recalcular_custo_materia_prima_do_item(item_id)
    service.recalcular_custo_total_do_item(item_id)

    repo = OrcamentoItemCusteioLinhaRepository(session)
    sep_atual = repo.get_by_id(sep.id)
    # The separator stays empty: no measures, no cost, no warning.
    assert sep_atual.comp_real is None
    assert sep_atual.area_m2 is None
    assert sep_atual.custo_mp is None
    assert sep_atual.custo_total is None
    assert sep_atual.observacoes is None
    # The real piece still gets its cost (separator did not interfere).
    peca_atual = repo.get_by_id(peca.id)
    assert peca_atual.custo_mp is not None and peca_atual.custo_mp > 0


def test_separador_nao_termina_bloco_de_divisao(session) -> None:
    item_id = _criar_item(session)
    div = _criar_linha(
        session, item_id, tipo_linha="DIVISAO_INDEPENDENTE", descricao="Corpo",
        qt_mod=Decimal("3"), comp="HM", larg="LM",
    )
    antes = _criar_linha(session, item_id, tipo_linha="PECA", descricao="Antes",
                         qt_und=Decimal("2"))
    service = OrcamentoItemCusteioLinhaService(session)
    sep = service.inserir_separador(item_id, antes.id)
    depois = _criar_linha(session, item_id, tipo_linha="PECA", descricao="Depois",
                          qt_und=Decimal("5"))

    service.recalcular_quantidades_do_item(item_id)

    repo = OrcamentoItemCusteioLinhaRepository(session)
    # The piece AFTER the separator still belongs to the division (3 x 5 = 15).
    assert repo.get_by_id(antes.id).quantidade == Decimal("6")   # 3 x 2
    assert repo.get_by_id(depois.id).quantidade == Decimal("15")  # 3 x 5
    assert repo.get_by_id(div.id).quantidade == Decimal("3")
    assert repo.get_by_id(sep.id).quantidade == Decimal("0")


def test_eliminar_separador(session) -> None:
    item_id = _criar_item(session)
    a = _criar_linha(session, item_id, descricao="A")
    service = OrcamentoItemCusteioLinhaService(session)
    sep = service.inserir_separador(item_id, a.id)
    assert "SEPARADOR" in _tipos(session, item_id)

    service.eliminar_linhas([sep.id])

    assert "SEPARADOR" not in _tipos(session, item_id)
    assert [l.id for l in OrcamentoItemCusteioLinhaRepository(session)
            .list_active_by_orcamento_item(item_id)] == [a.id]
