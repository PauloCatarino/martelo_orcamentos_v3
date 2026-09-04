"""Comparar o ValueSet do item com o material que está nas linhas de custeio.

É o que faltava no 260877_02: o ValueSet dizia Linho Cancun e treze linhas de
custeio continuavam a custar Branco, porque ninguém carregou no botão que leva
o ValueSet ao custeio.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import (
    Cliente,
    Orcamento,
    OrcamentoItem,
    OrcamentoItemCusteioLinha,
    OrcamentoItemValuesetLinha,
    OrcamentoVersao,
)
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


BRANCO = dict(ref_le="PLC0025", preco_liquido=Decimal("5.5717"))
LINHO = dict(ref_le="PLC0035", preco_liquido=Decimal("7.1232"))


@pytest.fixture()
def item(session: Session) -> OrcamentoItem:
    cliente = Cliente(nome="Cliente ValueSet", is_temporary=True)
    session.add(cliente)
    session.flush()
    orcamento = Orcamento(ano=2026, num_orcamento="260877", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()
    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=2,
        codigo_versao="260877_02",
        estado="Falta Orçamentar",
    )
    session.add(versao)
    session.flush()
    item = OrcamentoItem(
        orcamento_versao_id=versao.id,
        ordem=1,
        codigo="RP_01",
        tipo_item="ROUPEIRO_ABRIR",
        item="RP_01",
        quantidade=Decimal("1"),
        unidade="un",
    )
    session.add(item)
    session.flush()
    return item


def _opcao(session, item, **campos) -> OrcamentoItemValuesetLinha:
    base = dict(
        orcamento_item_id=item.id,
        chave="MATERIAL_LATERAIS",
        codigo_opcao="AGL_19_STANDARD",
        padrao=True,
        ordem=1,
        ativo=True,
    )
    base.update(campos)
    linha = OrcamentoItemValuesetLinha(**base)
    session.add(linha)
    session.flush()
    return linha


def _linha_custeio(session, item, **campos) -> OrcamentoItemCusteioLinha:
    base = dict(
        orcamento_item_id=item.id,
        tipo_linha="PECA",
        descricao="Lateral[2011]",
        def_peca_codigo="LATERAL_2011",
        chave_valueset="MATERIAL_LATERAIS",
        mat_default="AGL_19_STANDARD",
        quantidade=Decimal("2"),
        ativo=True,
    )
    base.update(campos)
    linha = OrcamentoItemCusteioLinha(**base)
    session.add(linha)
    session.flush()
    return linha


def test_deteta_a_linha_que_ficou_no_material_antigo(
    session: Session, item: OrcamentoItem
) -> None:
    _opcao(session, item, **LINHO)
    _linha_custeio(session, item, **BRANCO)

    divergencias = OrcamentoItemCusteioLinhaService(
        session
    ).listar_divergencias_valueset_do_item(item.id)

    assert len(divergencias) == 1
    divergencia = divergencias[0]
    assert divergencia.linha.ref_le == "PLC0025"
    assert divergencia.valueset_linha.ref_le == "PLC0035"
    assert divergencia.sugerido is True
    assert "Ref LE" in divergencia.campos
    assert "Preço líquido" in divergencia.campos


def test_linha_igual_ao_valueset_nao_e_divergencia(
    session: Session, item: OrcamentoItem
) -> None:
    _opcao(session, item, **LINHO)
    _linha_custeio(session, item, **LINHO)

    assert (
        OrcamentoItemCusteioLinhaService(session).listar_divergencias_valueset_do_item(
            item.id
        )
        == []
    )


def test_material_escolhido_a_mao_aparece_mas_vem_desmarcado(
    session: Session, item: OrcamentoItem
) -> None:
    _opcao(session, item, **LINHO)
    _linha_custeio(session, item, material_editado_localmente=True, **BRANCO)

    divergencias = OrcamentoItemCusteioLinhaService(
        session
    ).listar_divergencias_valueset_do_item(item.id)

    assert len(divergencias) == 1
    assert divergencias[0].sugerido is False


def test_opcao_que_ja_nao_existe_no_valueset_nao_e_adivinhada(
    session: Session, item: OrcamentoItem
) -> None:
    _opcao(session, item, **LINHO)
    _linha_custeio(session, item, mat_default="OPCAO_APAGADA", **BRANCO)

    assert (
        OrcamentoItemCusteioLinhaService(session).listar_divergencias_valueset_do_item(
            item.id
        )
        == []
    )


def test_divisoes_e_peca_composta_ficam_de_fora(
    session: Session, item: OrcamentoItem
) -> None:
    _opcao(session, item, **LINHO)
    _linha_custeio(session, item, tipo_linha="DIVISAO_INDEPENDENTE", **BRANCO)
    _linha_custeio(session, item, tipo_linha="PECA_COMPOSTA", **BRANCO)

    assert (
        OrcamentoItemCusteioLinhaService(session).listar_divergencias_valueset_do_item(
            item.id
        )
        == []
    )


def test_aplicar_escreve_o_material_do_valueset_na_linha(
    session: Session, item: OrcamentoItem
) -> None:
    opcao = _opcao(session, item, **LINHO)
    linha = _linha_custeio(session, item, **BRANCO)
    service = OrcamentoItemCusteioLinhaService(session)

    atualizadas = service.aplicar_divergencias_valueset([(linha.id, opcao.id)])

    assert atualizadas == 1
    session.refresh(linha)
    assert linha.ref_le == "PLC0035"
    assert linha.preco_liquido == Decimal("7.1232")
    assert linha.material_editado_localmente is False
    assert service.listar_divergencias_valueset_do_item(item.id) == []
