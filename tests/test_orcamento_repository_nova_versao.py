"""Tests for duplicating a budget version (margins inheritance, phase 8T.1).

Uses an in-memory SQLite database; BigInteger primary keys are rendered as
INTEGER on SQLite so autoincrement works (test-only compile rule).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import BigInteger, select
from sqlalchemy.orm import Session

from app.domain.orcamento_estados import ESTADO_INICIAL
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    Cliente,
    Orcamento,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoItemCusteioLinhaOperacao,
    OrcamentoItemModulo,
    OrcamentoItemValuesetLinha,
    OrcamentoItemValuesetLinhaOperacao,
    OrcamentoItemVariavel,
    OrcamentoValuesetLinha,
    OrcamentoVersao,
    OrcamentoVersaoPlacaNaoStock,
)
from app.repositories.orcamento_repository import OrcamentoRepository


def _criar_orcamento_com_versao(session: Session) -> OrcamentoVersao:
    cliente = Cliente(nome="Cliente Teste", is_temporary=True)
    session.add(cliente)
    session.flush()

    orcamento = Orcamento(ano=2026, num_orcamento="260001", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()

    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="260001_01",
        estado="Enviado",
        preco_total=Decimal("500.00"),
        tipo_producao_default="SERIE",
        margem_lucro_pct=Decimal("10"),
        margem_mp_pct=Decimal("15"),
        margem_mao_obra_pct=Decimal("5"),
        margem_acabamentos_pct=Decimal("5"),
        custos_administrativos_pct=Decimal("3"),
    )
    session.add(versao)
    session.flush()
    return versao


def test_nova_versao_herda_margens_da_anterior(session: Session) -> None:
    origem = _criar_orcamento_com_versao(session)
    repository = OrcamentoRepository(session)

    criada = repository.criar_nova_versao(origem.id)

    nova = session.get(OrcamentoVersao, criada.orcamento_versao_id)
    assert criada.numero_versao == 2
    assert criada.codigo_versao == "260001_02"
    assert nova.margem_lucro_pct == Decimal("10")
    assert nova.margem_mp_pct == Decimal("15")
    assert nova.margem_mao_obra_pct == Decimal("5")
    assert nova.margem_acabamentos_pct == Decimal("5")
    assert nova.custos_administrativos_pct == Decimal("3")
    # The production default travels with the version; the new version starts
    # with the canonical initial status and records where its price came from.
    assert nova.tipo_producao_default == "SERIE"
    assert nova.estado == ESTADO_INICIAL
    assert nova.preco_total == Decimal("0")
    assert nova.preco_origem == Decimal("500.00")


def test_nova_versao_usa_proximo_numero(session: Session) -> None:
    origem = _criar_orcamento_com_versao(session)
    repository = OrcamentoRepository(session)

    primeira = repository.criar_nova_versao(origem.id)
    segunda = repository.criar_nova_versao(primeira.orcamento_versao_id)

    assert segunda.numero_versao == 3
    assert segunda.codigo_versao == "260001_03"


def test_nova_versao_de_versao_inexistente_falha(session: Session) -> None:
    repository = OrcamentoRepository(session)

    with pytest.raises(ValueError, match="orcamento_versao"):
        repository.criar_nova_versao(999)


def test_get_cliente_id_by_versao(session: Session) -> None:
    origem = _criar_orcamento_com_versao(session)
    repository = OrcamentoRepository(session)

    cliente_id = repository.get_cliente_id_by_versao(origem.id)

    assert cliente_id is not None
    assert repository.get_cliente_id_by_versao(999) is None


def test_duplicar_versao_profunda(session: Session) -> None:
    origem = _criar_orcamento_profundo(session)
    repository = OrcamentoRepository(session)

    criada = repository.duplicar_versao_profunda(origem.id, created_by_id=7)

    nova = session.get(OrcamentoVersao, criada.orcamento_versao_id)
    assert criada.orcamento_id == origem.orcamento_id
    assert criada.numero_versao == 2
    assert criada.codigo_versao == "260001_02"
    assert nova.orcamento_id == origem.orcamento_id
    assert nova.estado == ESTADO_INICIAL
    assert nova.preco_total == origem.preco_total
    assert nova.preco_origem == origem.preco_total
    assert nova.tipo_producao_default == origem.tipo_producao_default
    assert nova.is_locked is False
    assert nova.locked_at is None
    assert nova.created_by_id == 7
    assert nova.updated_by_id == 7

    origem_items = _items_da_versao(session, origem.id)
    nova_items = _items_da_versao(session, nova.id)
    origem_item_ids = [item.id for item in origem_items]
    nova_item_ids = [item.id for item in nova_items]

    assert len(nova_items) == len(origem_items) == 2
    assert set(nova_item_ids).isdisjoint(origem_item_ids)
    assert _count_by_ids(session, OrcamentoItemVariavel, "item_id", origem_item_ids) == 2
    assert _count_by_ids(session, OrcamentoItemVariavel, "item_id", nova_item_ids) == 2
    assert _count_by_ids(session, OrcamentoItemModulo, "orcamento_item_id", origem_item_ids) == 2
    assert _count_by_ids(session, OrcamentoItemModulo, "orcamento_item_id", nova_item_ids) == 2
    assert (
        _count_by_ids(session, OrcamentoItemCusteioLinha, "orcamento_item_id", origem_item_ids)
        == 4
    )
    assert (
        _count_by_ids(session, OrcamentoItemCusteioLinha, "orcamento_item_id", nova_item_ids)
        == 4
    )
    assert (
        _count_by_ids(session, OrcamentoItemValuesetLinha, "orcamento_item_id", origem_item_ids)
        == 2
    )
    assert (
        _count_by_ids(session, OrcamentoItemValuesetLinha, "orcamento_item_id", nova_item_ids)
        == 2
    )
    assert _count_by_versao(session, OrcamentoValuesetLinha, origem.id) == 1
    assert _count_by_versao(session, OrcamentoValuesetLinha, nova.id) == 1
    assert _count_by_versao(session, OrcamentoVersaoPlacaNaoStock, origem.id) == 1
    assert _count_by_versao(session, OrcamentoVersaoPlacaNaoStock, nova.id) == 1

    origem_modulo_ids = _ids_by_ids(
        session, OrcamentoItemModulo, "orcamento_item_id", origem_item_ids
    )
    nova_modulo_ids = _ids_by_ids(
        session, OrcamentoItemModulo, "orcamento_item_id", nova_item_ids
    )
    origem_linha_ids = _ids_by_ids(
        session, OrcamentoItemCusteioLinha, "orcamento_item_id", origem_item_ids
    )
    nova_linhas = _rows_by_ids(
        session, OrcamentoItemCusteioLinha, "orcamento_item_id", nova_item_ids
    )
    nova_linha_ids = {linha.id for linha in nova_linhas}

    linhas_com_pai = [linha for linha in nova_linhas if linha.linha_pai_id is not None]
    assert linhas_com_pai
    assert all(linha.linha_pai_id in nova_linha_ids for linha in linhas_com_pai)
    assert all(linha.linha_pai_id not in origem_linha_ids for linha in linhas_com_pai)

    linhas_com_modulo = [
        linha for linha in nova_linhas if linha.orcamento_item_modulo_id is not None
    ]
    assert linhas_com_modulo
    assert all(
        linha.orcamento_item_modulo_id in nova_modulo_ids
        for linha in linhas_com_modulo
    )
    assert all(
        linha.orcamento_item_modulo_id not in origem_modulo_ids
        for linha in linhas_com_modulo
    )

    novo_vsl = session.execute(
        select(OrcamentoValuesetLinha).where(
            OrcamentoValuesetLinha.orcamento_versao_id == nova.id
        )
    ).scalar_one()
    novos_item_vsl = _rows_by_ids(
        session, OrcamentoItemValuesetLinha, "orcamento_item_id", nova_item_ids
    )
    assert {linha.origem_orcamento_valueset_linha_id for linha in novos_item_vsl} == {
        novo_vsl.id
    }
    assert {linha.origem_orcamento_versao_id for linha in novos_item_vsl} == {nova.id}

    # Operations of the item ValueSet lines and of the costing lines must be
    # copied too (2 items × 1 each), else a re-costing drops production costs.
    origem_vsl_ids = _ids_by_ids(
        session, OrcamentoItemValuesetLinha, "orcamento_item_id", origem_item_ids
    )
    nova_vsl_ids = _ids_by_ids(
        session, OrcamentoItemValuesetLinha, "orcamento_item_id", nova_item_ids
    )
    assert _count_by_ids(
        session, OrcamentoItemValuesetLinhaOperacao,
        "orcamento_item_valueset_linha_id", list(origem_vsl_ids),
    ) == 2
    assert _count_by_ids(
        session, OrcamentoItemValuesetLinhaOperacao,
        "orcamento_item_valueset_linha_id", list(nova_vsl_ids),
    ) == 2
    assert _count_by_ids(
        session, OrcamentoItemCusteioLinhaOperacao, "linha_id", list(origem_linha_ids)
    ) == 2
    assert _count_by_ids(
        session, OrcamentoItemCusteioLinhaOperacao, "linha_id", list(nova_linha_ids)
    ) == 2


def _criar_orcamento_profundo(session: Session) -> OrcamentoVersao:
    cliente = Cliente(nome="Cliente Profundo", is_temporary=True)
    session.add(cliente)
    session.flush()

    orcamento = Orcamento(ano=2026, num_orcamento="260001", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()

    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="260001_01",
        estado="Enviado",
        preco_total=Decimal("1234.56"),
        preco_origem=Decimal("1000.00"),
        tipo_producao_default="SERIE",
        margem_lucro_pct=Decimal("10"),
        margem_mp_pct=Decimal("11"),
        margem_mao_obra_pct=Decimal("12"),
        margem_acabamentos_pct=Decimal("13"),
        custos_administrativos_pct=Decimal("14"),
        is_locked=True,
        locked_at=datetime(2026, 6, 1, 10, 0),
    )
    session.add(versao)
    session.flush()

    valueset_versao = OrcamentoValuesetLinha(
        orcamento_versao_id=versao.id,
        chave="MATERIAL",
        codigo_opcao="MDF",
        nome_opcao="MDF Branco",
        padrao=True,
        ordem=1,
        ref_le="MDF-19",
        preco_liquido=Decimal("12.34"),
        ativo=True,
    )
    session.add(valueset_versao)
    session.flush()

    session.add(
        OrcamentoVersaoPlacaNaoStock(
            orcamento_versao_id=versao.id,
            ref_le="MDF-19",
            descricao="MDF Branco",
            esp=Decimal("19"),
            nao_stock=True,
        )
    )
    session.flush()

    for ordem in (1, 2):
        _criar_item_profundo(session, versao.id, valueset_versao.id, ordem)

    return versao


def _criar_item_profundo(
    session: Session,
    versao_id: int,
    valueset_versao_id: int,
    ordem: int,
) -> OrcamentoItem:
    item = OrcamentoItem(
        orcamento_versao_id=versao_id,
        ordem=ordem,
        codigo=f"IT-{ordem}",
        tipo_item="MOVEL",
        item=f"Item {ordem}",
        descricao=f"Descricao {ordem}",
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("617.28"),
        preco_total=Decimal("617.28"),
        ajuste_eur=Decimal("2.50"),
        preco_manual=ordem == 2,
        tipo_producao="SERIE",
    )
    session.add(item)
    session.flush()

    session.add(
        OrcamentoItemVariavel(
            item_id=item.id,
            nome=f"LARGURA_{ordem}",
            valor=Decimal("800"),
            unidade="mm",
            ordem=1,
        )
    )

    modulo = OrcamentoItemModulo(
        orcamento_item_id=item.id,
        ordem=1,
        nome=f"Modulo {ordem}",
        descricao="Modulo teste",
        quantidade=Decimal("1"),
    )
    session.add(modulo)
    session.flush()

    item_vsl = OrcamentoItemValuesetLinha(
        orcamento_item_id=item.id,
        chave="MATERIAL",
        codigo_opcao="MDF",
        nome_opcao="MDF Branco",
        padrao=True,
        ordem=1,
        origem_orcamento_valueset_linha_id=valueset_versao_id,
        origem_orcamento_versao_id=versao_id,
        herdado_do_orcamento=True,
        ativo=True,
    )
    session.add(item_vsl)
    session.flush()

    session.add(
        OrcamentoItemValuesetLinhaOperacao(
            orcamento_item_valueset_linha_id=item_vsl.id,
            def_operacao_id=1,
            ordem=1,
            acao="ADICIONAR",
            tempo_por_unidade_minutos=Decimal("3"),
            ativo=True,
        )
    )

    cabecalho = OrcamentoItemCusteioLinha(
        orcamento_item_id=item.id,
        orcamento_item_modulo_id=modulo.id,
        tipo_linha="PECA_COMPOSTA",
        descricao=f"Composto {ordem}",
        nivel=0,
        ordem=1,
        quantidade=Decimal("1"),
        custo_total=Decimal("50"),
        preco_total=Decimal("75"),
        ativo=True,
    )
    session.add(cabecalho)
    session.flush()

    filho = OrcamentoItemCusteioLinha(
        orcamento_item_id=item.id,
        linha_pai_id=cabecalho.id,
        tipo_linha="PECA",
        descricao=f"Filho {ordem}",
        nivel=1,
        ordem=2,
        quantidade=Decimal("2"),
        qt_mod=Decimal("1"),
        qt_und=Decimal("2"),
        custo_mp=Decimal("20"),
        custo_total=Decimal("20"),
        preco_total=Decimal("30"),
        ativo=True,
    )
    session.add(filho)
    session.flush()

    session.add(
        OrcamentoItemCusteioLinhaOperacao(
            linha_id=filho.id,
            def_operacao_id=1,
            ordem=1,
            codigo="OP1",
            nome="Operacao local",
            origem="LOCAL",
            ativo=True,
        )
    )
    session.flush()

    return item


def _items_da_versao(session: Session, versao_id: int) -> list[OrcamentoItem]:
    return list(
        session.execute(
            select(OrcamentoItem)
            .where(OrcamentoItem.orcamento_versao_id == versao_id)
            .order_by(OrcamentoItem.ordem.asc())
        ).scalars()
    )


def _rows_by_ids(session: Session, model, field: str, ids: list[int]):
    coluna = getattr(model, field)
    return list(session.execute(select(model).where(coluna.in_(ids))).scalars())


def _ids_by_ids(session: Session, model, field: str, ids: list[int]) -> set[int]:
    return {row.id for row in _rows_by_ids(session, model, field, ids)}


def _count_by_ids(session: Session, model, field: str, ids: list[int]) -> int:
    return len(_rows_by_ids(session, model, field, ids))


def _count_by_versao(session: Session, model, versao_id: int) -> int:
    return len(
        list(
            session.execute(
                select(model).where(model.orcamento_versao_id == versao_id)
            ).scalars()
        )
    )
