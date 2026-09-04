"""Trocar o material de uma linha não pode calar a regra da quantidade.

No 260881_01, um fundo de 900×600 ficou com 1 pé em vez de 6. A regra
PES_NIVELADORES não corria porque a condição olhava para o
``editado_localmente`` — uma bandeira que quer dizer «o MATERIAL desta linha foi
trocado à mão». Bastou escolher outro pé nivelador no dropdown «Mat. default»
para a quantidade congelar, em silêncio.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    Cliente,
    DefPeca,
    DefPecaComponente,
    DefRegraQuantidade,
    Orcamento,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoVersao,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


PES_NIVELADORES = (
    "4 if COMP < 650 and LARG < 800 else 6 if COMP >= 650 and LARG < 800 else 8"
)


@pytest.fixture()
def bloco(session: Session):
    """Um FUNDO[2200]+PES de 900×600: pela regra são 6 pés."""
    cliente = Cliente(nome="Cliente Lavandaria", is_temporary=True)
    session.add(cliente)
    session.flush()
    orcamento = Orcamento(ano=2026, num_orcamento="260881", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()
    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="260881_01",
        estado="Falta Orçamentar",
    )
    session.add(versao)
    session.flush()
    item = OrcamentoItem(
        orcamento_versao_id=versao.id,
        ordem=1,
        codigo="LAVANDARIA",
        tipo_item="OUTRO",
        item="LAVANDARIA",
        quantidade=Decimal("1"),
        unidade="un",
    )
    session.add(item)
    session.flush()

    composta = DefPeca(codigo="FUNDO_2200+PES", nome="FUNDO[2200]+PES", ativo=True)
    pes = DefPeca(codigo="PES", nome="Pés", ativo=True)
    session.add_all([composta, pes])
    session.flush()

    regra = DefRegraQuantidade(
        codigo="PES_NIVELADORES",
        nome="Pés niveladores",
        expressao=PES_NIVELADORES,
        ativo=True,
    )
    session.add(regra)
    session.flush()

    componente = DefPecaComponente(
        def_peca_pai_id=composta.id,
        tipo_componente="FERRAGEM",
        def_peca_componente_id=pes.id,
        ordem=2,
        quantidade=Decimal("1"),
        def_regra_quantidade_id=regra.id,
        ativo=True,
    )
    session.add(componente)
    session.flush()

    cabecalho = OrcamentoItemCusteioLinha(
        orcamento_item_id=item.id,
        tipo_linha="PECA_COMPOSTA",
        descricao="FUNDO[2200]+PES",
        def_peca_codigo="FUNDO_2200+PES",
        qt_mod=Decimal("1"),
        qt_und=Decimal("1"),
        quantidade=Decimal("1"),
        ativo=True,
    )
    session.add(cabecalho)
    session.flush()

    fundo = OrcamentoItemCusteioLinha(
        orcamento_item_id=item.id,
        linha_pai_id=cabecalho.id,
        nivel=1,
        ordem=1,
        tipo_linha="PECA",
        descricao="Fundo[2200]",
        def_peca_codigo="FUNDO_2200",
        qt_mod=Decimal("1"),
        qt_und=Decimal("1"),
        quantidade=Decimal("1"),
        comp_real=Decimal("900"),
        larg_real=Decimal("600"),
        esp_real=Decimal("19"),
        ativo=True,
    )
    session.add(fundo)

    linha_pes = OrcamentoItemCusteioLinha(
        orcamento_item_id=item.id,
        linha_pai_id=cabecalho.id,
        nivel=1,
        ordem=2,
        tipo_linha="FERRAGEM",
        descricao="Pés",
        def_peca_codigo="PES",
        origem_id=componente.id,
        qt_mod=Decimal("1"),
        qt_und=Decimal("1"),
        quantidade=Decimal("1"),
        ativo=True,
    )
    session.add(linha_pes)
    session.flush()

    return item, linha_pes


def test_a_regra_calcula_os_seis_pes(session: Session, bloco) -> None:
    item, linha_pes = bloco

    OrcamentoItemCusteioLinhaService(session).aplicar_regras_quantidade_do_item(item.id)

    session.refresh(linha_pes)
    assert linha_pes.qt_und == Decimal("6")


def test_trocar_o_material_nao_congela_a_quantidade(session: Session, bloco) -> None:
    """Era este o bug: o pé nivelador foi trocado e a regra parou."""
    item, linha_pes = bloco
    linha_pes.editado_localmente = True
    linha_pes.material_editado_localmente = True
    linha_pes.ref_le = "FER0059"
    session.flush()

    OrcamentoItemCusteioLinhaService(session).aplicar_regras_quantidade_do_item(item.id)

    session.refresh(linha_pes)
    assert linha_pes.qt_und == Decimal("6")
    assert "regra ignorada" not in (linha_pes.observacoes or "")


def test_quantidade_escrita_a_mao_e_respeitada(session: Session, bloco) -> None:
    item, linha_pes = bloco
    linha_pes.qt_und = Decimal("4")
    linha_pes.quantidade_editada_localmente = True
    session.flush()

    OrcamentoItemCusteioLinhaService(session).aplicar_regras_quantidade_do_item(item.id)

    session.refresh(linha_pes)
    assert linha_pes.qt_und == Decimal("4")
    assert "regra ignorada" in (linha_pes.observacoes or "")


def test_editar_a_quantidade_marca_a_linha(session: Session, bloco) -> None:
    item, linha_pes = bloco
    service = OrcamentoItemCusteioLinhaService(session)

    service.atualizar_medidas_linha(
        linha_pes.id,
        qt_mod=Decimal("1"),
        qt_und=Decimal("4"),
        comp=None,
        larg=None,
        esp=None,
        propagar_item=False,
    )

    session.refresh(linha_pes)
    assert linha_pes.quantidade_editada_localmente is True
    # E a marca aguenta a passagem das regras.
    service.aplicar_regras_quantidade_do_item(item.id)
    session.refresh(linha_pes)
    assert linha_pes.qt_und == Decimal("4")


def test_mudar_so_uma_medida_nao_marca_a_quantidade(session: Session, bloco) -> None:
    """Colar Comp/Larg do Excel não pode calar a regra da quantidade."""
    item, linha_pes = bloco
    service = OrcamentoItemCusteioLinhaService(session)

    service.atualizar_medidas_linha(
        linha_pes.id,
        qt_mod=Decimal("1"),
        qt_und=Decimal("1"),
        comp="800",
        larg=None,
        esp=None,
        propagar_item=False,
    )

    session.refresh(linha_pes)
    assert linha_pes.quantidade_editada_localmente is False


def test_repor_a_quantidade_da_regra(session: Session, bloco) -> None:
    item, linha_pes = bloco
    linha_pes.qt_und = Decimal("4")
    linha_pes.quantidade_editada_localmente = True
    linha_pes.observacoes = (
        "Regra de quantidade PES_NIVELADORES: qt_und definido manualmente "
        "(regra ignorada)."
    )
    session.flush()
    service = OrcamentoItemCusteioLinhaService(session)

    assert service.repor_quantidade_da_regra([linha_pes.id]) == 1

    session.refresh(linha_pes)
    assert linha_pes.quantidade_editada_localmente is False
    assert linha_pes.observacoes is None

    service.aplicar_regras_quantidade_do_item(item.id)
    session.refresh(linha_pes)
    assert linha_pes.qt_und == Decimal("6")
