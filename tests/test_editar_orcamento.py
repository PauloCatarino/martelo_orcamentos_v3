"""Tests for editing a budget's general data (phase 9.0)."""

from __future__ import annotations

import pytest


from app.domain.orcamento_estados import ESTADO_INICIAL
import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import Cliente, Orcamento, OrcamentoVersao, OrcamentoVersaoEvento
from app.repositories.orcamento_repository import OrcamentoRepository
from app.services.orcamento_service import (
    CriarOrcamentoSimplesData,
    EditarOrcamentoData,
    OrcamentoService,
)


def _criar_orcamento(session) -> tuple[int, int]:
    """Create a simple budget and return its orcamento_id and version id."""
    cliente = Cliente(nome="Cliente X", is_temporary=True)
    session.add(cliente)
    session.flush()

    service = OrcamentoService(session)
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente.id,
            obra="Obra Inicial",
            descricao="Descricao Inicial",
            localizacao="Local Inicial",
            ref_cliente="REF-1",
            created_by_id=None,
            ano=2026,
        )
    )
    orcamento = service.list_orcamentos()[0]
    return orcamento.orcamento_id, orcamento.orcamento_versao_id


def test_criar_orcamento_usa_estado_inicial(session) -> None:
    _orcamento_id, orcamento_versao_id = _criar_orcamento(session)

    versao = session.get(OrcamentoVersao, orcamento_versao_id)
    assert versao.estado == ESTADO_INICIAL


def test_editar_orcamento_persiste_os_campos_e_estado(session) -> None:
    orcamento_id, orcamento_versao_id = _criar_orcamento(session)
    service = OrcamentoService(session)

    resultado = service.editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra Nova",
            descricao="Descricao Nova",
            localizacao="Local Novo",
            ref_cliente="REF-2",
            estado="Enviado",
        ),
        orcamento_versao_id=orcamento_versao_id,
    )

    assert resultado is True
    versao = session.get(OrcamentoVersao, orcamento_versao_id)
    assert versao.obra == "Obra Nova"
    assert versao.descricao == "Descricao Nova"
    assert versao.localizacao == "Local Novo"
    # ref_cliente stays on the parent (shared by all versions).
    assert session.get(Orcamento, orcamento_id).ref_cliente == "REF-2"
    assert versao.estado == "Enviado"
    evento = session.query(OrcamentoVersaoEvento).one()
    assert evento.orcamento_versao_id == orcamento_versao_id
    assert evento.tipo == "estado"
    assert evento.descricao == "Estado: Falta Or\u00e7amentar \u2192 Enviado"


def test_editar_orcamento_nao_cria_evento_se_estado_nao_mudar(session) -> None:
    orcamento_id, orcamento_versao_id = _criar_orcamento(session)

    OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra Nova",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
        ),
        orcamento_versao_id=orcamento_versao_id,
    )

    assert session.query(OrcamentoVersaoEvento).count() == 0


def test_editar_orcamento_guarda_updated_by_id(session) -> None:
    orcamento_id, orcamento_versao_id = _criar_orcamento(session)

    OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra Nova",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
        ),
        updated_by_id=None,
        orcamento_versao_id=orcamento_versao_id,
    )

    versao = session.get(OrcamentoVersao, orcamento_versao_id)
    # Optional fields cleared; obra kept. These belong to the version now.
    assert versao.obra == "Obra Nova"
    assert versao.descricao is None
    assert versao.localizacao is None
    assert session.get(Orcamento, orcamento_id).ref_cliente is None


def test_editar_orcamento_inexistente_devolve_false(session) -> None:
    resultado = OrcamentoService(session).editar_orcamento(
        9999,
        EditarOrcamentoData(
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
        ),
        orcamento_versao_id=9999,
    )

    assert resultado is False


def test_editar_orcamento_aceita_obra_vazia(session) -> None:
    orcamento_id, orcamento_versao_id = _criar_orcamento(session)

    resultado = OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="   ",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
        ),
        orcamento_versao_id=orcamento_versao_id,
    )

    assert resultado is True
    assert session.get(OrcamentoVersao, orcamento_versao_id).obra == ""


def test_editar_orcamento_troca_o_cliente(session) -> None:
    outro = Cliente(nome="Cliente Y", is_temporary=True)
    session.add(outro)
    session.flush()

    orcamento_id, orcamento_versao_id = _criar_orcamento(session)

    OrcamentoService(session).editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra",
            descricao=None,
            localizacao=None,
            ref_cliente=None,
            estado=ESTADO_INICIAL,
            cliente_id=outro.id,
        ),
        orcamento_versao_id=orcamento_versao_id,
    )

    assert session.get(Orcamento, orcamento_id).cliente_id == outro.id


def test_editar_uma_versao_nao_altera_as_outras(session) -> None:
    orcamento_id, versao_1_id = _criar_orcamento(session)
    service = OrcamentoService(session)
    # Versão 02 criada a partir da 01 (herda os dados gerais iniciais).
    v2 = service.duplicar_versao(versao_1_id)
    versao_2_id = v2.orcamento_versao_id

    service.editar_orcamento(
        orcamento_id,
        EditarOrcamentoData(
            obra="Obra so v1",
            descricao="Desc so v1",
            localizacao="Local so v1",
            ref_cliente="REF-1",
            estado="Enviado",
            enc_phc="111",
            info_1="Info1 v1",
            info_2="Info2 v1",
        ),
        orcamento_versao_id=versao_1_id,
    )

    v1 = session.get(OrcamentoVersao, versao_1_id)
    v2r = session.get(OrcamentoVersao, versao_2_id)
    # A versão editada recebeu as alterações...
    assert (
        v1.obra,
        v1.descricao,
        v1.localizacao,
        v1.info_1,
        v1.info_2,
        v1.estado,
    ) == ("Obra so v1", "Desc so v1", "Local so v1", "Info1 v1", "Info2 v1", "Enviado")
    # ...e a outra versão manteve os valores herdados, sem contágio.
    assert (v2r.obra, v2r.descricao, v2r.localizacao) == (
        "Obra Inicial",
        "Descricao Inicial",
        "Local Inicial",
    )
    assert v2r.info_1 is None and v2r.info_2 is None
    assert v2r.estado == ESTADO_INICIAL


def test_lista_marca_orcamento_com_preco_manual(session) -> None:
    from app.models import OrcamentoItem
    from decimal import Decimal

    _orcamento_id, orcamento_versao_id = _criar_orcamento(session)
    service = OrcamentoService(session)

    # sem itens manuais -> tem_preco_manual False
    resumo = service.list_orcamentos()[0]
    assert resumo.tem_preco_manual is False

    # adicionar um item com preço manual -> passa a True
    session.add(
        OrcamentoItem(
            orcamento_versao_id=orcamento_versao_id,
            ordem=1,
            item="Externo",
            quantidade=Decimal("1"),
            preco_unitario=Decimal("100"),
            preco_total=Decimal("100"),
            preco_manual=True,
        )
    )
    session.flush()
    resumo = service.list_orcamentos()[0]
    assert resumo.tem_preco_manual is True


def test_find_by_ref_cliente_pesquisa_trim_case_insensitive(session) -> None:
    cliente_a = Cliente(nome="Cliente A", is_temporary=True)
    cliente_b = Cliente(nome="Cliente B", is_temporary=True)
    session.add_all([cliente_a, cliente_b])
    session.flush()
    cliente_a_id = cliente_a.id
    cliente_b_id = cliente_b.id

    service = OrcamentoService(session)
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente_a_id,
            obra="Obra A",
            descricao=None,
            localizacao=None,
            ref_cliente="  Ref-Cliente-X  ",
            ano=2025,
        )
    )
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente_b_id,
            obra="Obra B",
            descricao=None,
            localizacao=None,
            ref_cliente="ref-cliente-x",
            ano=2026,
        )
    )
    service.criar_orcamento_simples(
        CriarOrcamentoSimplesData(
            cliente_id=cliente_a_id,
            obra="Obra C",
            descricao=None,
            localizacao=None,
            ref_cliente="OUTRA",
            ano=2026,
        )
    )

    resultados = OrcamentoRepository(session).find_by_ref_cliente(" REF-CLIENTE-X ")

    assert [
        (orcamento.ano, orcamento.ref_cliente, orcamento.cliente_nome)
        for orcamento in resultados
    ] == [
        (2026, "ref-cliente-x", "Cliente B"),
        (2025, "  Ref-Cliente-X  ", "Cliente A"),
    ]
    assert OrcamentoRepository(session).find_by_ref_cliente("   ") == []
