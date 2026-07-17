"""Priority-based resolution of ValueSet lines (prioridade replaces padrao).

The active line with the lowest prioridade (1 = first choice) wins the
automatic choice in costing; NULL priorities go last, tie broken by id.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import OrcamentoItem, OrcamentoItemValuesetLinha, OrcamentoValuesetLinha
from app.repositories.def_peca_repository import DefPecaRepository
from app.repositories.orcamento_item_valueset_linha_repository import (
    OrcamentoItemValuesetLinhaRepository,
)
from app.repositories.orcamento_valueset_linha_repository import (
    OrcamentoValuesetLinhaRepository,
)
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


CHAVE = "FERRAGEM_DOBRADICA"


def _criar_item(session) -> int:
    item = OrcamentoItem(
        orcamento_versao_id=1, ordem=1, tipo_item="OUTRO", item="Item",
        quantidade=Decimal("1"), altura=Decimal("2000"),
        largura=Decimal("1000"), profundidade=Decimal("500"),
    )
    session.add(item)
    session.flush()
    return item.id


def _linha_item(session, item_id, codigo_opcao, *, prioridade=None, ativo=True):
    linha = OrcamentoItemValuesetLinha(
        orcamento_item_id=item_id, chave=CHAVE, codigo_opcao=codigo_opcao,
        nome_opcao=codigo_opcao, prioridade=prioridade, ativo=ativo,
        ref_le=f"LE_{codigo_opcao}", unidade="und",
        preco_liquido=Decimal("1.50"),
    )
    session.add(linha)
    session.flush()
    return linha


def _linha_versao(session, versao_id, codigo_opcao, *, prioridade=None, ativo=True):
    linha = OrcamentoValuesetLinha(
        orcamento_versao_id=versao_id, chave=CHAVE, codigo_opcao=codigo_opcao,
        nome_opcao=codigo_opcao, prioridade=prioridade, ativo=ativo,
    )
    session.add(linha)
    session.flush()
    return linha


# --- (a) resolução por prioridade no repositório do item ---------------------


def test_prioridade_mais_baixa_ganha(session) -> None:
    item_id = _criar_item(session)
    _linha_item(session, item_id, "B", prioridade=2)
    vencedora = _linha_item(session, item_id, "A", prioridade=1)
    _linha_item(session, item_id, "C", prioridade=3)

    resolvida = OrcamentoItemValuesetLinhaRepository(session).get_default_by_item_chave(
        item_id, CHAVE
    )

    assert resolvida is not None
    assert resolvida.id == vencedora.id
    assert resolvida.codigo_opcao == "A"


def test_todas_null_ganha_menor_id(session) -> None:
    item_id = _criar_item(session)
    primeira = _linha_item(session, item_id, "B")
    _linha_item(session, item_id, "A")
    _linha_item(session, item_id, "C")

    resolvida = OrcamentoItemValuesetLinhaRepository(session).get_default_by_item_chave(
        item_id, CHAVE
    )

    assert resolvida is not None
    assert resolvida.id == primeira.id


def test_prioridade_null_vai_para_o_fim(session) -> None:
    item_id = _criar_item(session)
    _linha_item(session, item_id, "SEM_PRIORIDADE")  # menor id, mas NULL
    com_prioridade = _linha_item(session, item_id, "COM_PRIORIDADE", prioridade=5)

    resolvida = OrcamentoItemValuesetLinhaRepository(session).get_default_by_item_chave(
        item_id, CHAVE
    )

    assert resolvida is not None
    assert resolvida.id == com_prioridade.id


def test_prioridade_1_inativa_passa_a_2(session) -> None:
    item_id = _criar_item(session)
    _linha_item(session, item_id, "A", prioridade=1, ativo=False)
    segunda = _linha_item(session, item_id, "B", prioridade=2)

    resolvida = OrcamentoItemValuesetLinhaRepository(session).get_default_by_item_chave(
        item_id, CHAVE
    )

    assert resolvida is not None
    assert resolvida.id == segunda.id


def test_versao_resolve_pela_mesma_regra(session) -> None:
    _linha_versao(session, 1, "B", prioridade=2)
    vencedora = _linha_versao(session, 1, "A", prioridade=1)
    _linha_versao(session, 1, "C")  # NULL vai para o fim

    resolvida = OrcamentoValuesetLinhaRepository(session).get_default_by_versao_chave(
        1, CHAVE
    )

    assert resolvida is not None
    assert resolvida.id == vencedora.id


def test_dropdown_ordena_por_prioridade_null_no_fim(session) -> None:
    item_id = _criar_item(session)
    _linha_item(session, item_id, "SEM")  # NULL
    _linha_item(session, item_id, "TRES", prioridade=3)
    _linha_item(session, item_id, "UM", prioridade=1)

    opcoes = OrcamentoItemValuesetLinhaRepository(session).list_by_item_chave(
        item_id, CHAVE
    )

    assert [opcao.codigo_opcao for opcao in opcoes] == ["UM", "TRES", "SEM"]


# --- (c) integração custeio: mat_default segue a prioridade ------------------


def _peca_ferragem(session):
    return DefPecaRepository(session).create_def_peca(
        codigo="DOBRADICA", nome="Dobradiça", descricao=None, grupo=None,
        tipo_peca="SIMPLES", chave_valueset_material=CHAVE,
    )


def _linhas_custeio(session, item_id):
    return OrcamentoItemCusteioLinhaRepository(session).list_active_by_orcamento_item(
        item_id
    )


def test_inserir_peca_usa_opcao_prioridade_1(session) -> None:
    item_id = _criar_item(session)
    _linha_item(session, item_id, "SALICE", prioridade=2)
    _linha_item(session, item_id, "BLUM", prioridade=1)
    peca = _peca_ferragem(session)

    service = OrcamentoItemCusteioLinhaService(session)
    result = service.adicionar_pecas_da_biblioteca(item_id, [peca.id])

    assert result.criadas == 1
    linha = _linhas_custeio(session, item_id)[0]
    assert linha.mat_default == "BLUM"
    assert linha.ref_le == "LE_BLUM"


def test_mudar_prioridades_e_reinserir_muda_a_escolha(session) -> None:
    item_id = _criar_item(session)
    salice = _linha_item(session, item_id, "SALICE", prioridade=2)
    blum = _linha_item(session, item_id, "BLUM", prioridade=1)
    peca = _peca_ferragem(session)
    service = OrcamentoItemCusteioLinhaService(session)

    service.adicionar_pecas_da_biblioteca(item_id, [peca.id])
    assert _linhas_custeio(session, item_id)[0].mat_default == "BLUM"

    # Swap priorities: SALICE becomes the first choice.
    salice.prioridade = 1
    blum.prioridade = 2
    session.flush()

    service.adicionar_pecas_da_biblioteca(item_id, [peca.id])
    linhas = _linhas_custeio(session, item_id)
    assert linhas[-1].mat_default == "SALICE"
    assert linhas[-1].ref_le == "LE_SALICE"
