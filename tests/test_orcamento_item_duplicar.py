"""Tests for duplicating a single budget item ("Gravar como…").

Deep-copies one item and all its owned children (variables, modules, ValueSet
lines, costing lines) inside the SAME version, remapping the internal foreign
keys, then applies the edited dialog values to the new item.

Uses the in-memory SQLite database from the shared ``session`` fixture.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

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
)
from app.services.orcamento_item_service import (
    EditarOrcamentoItemSimplesData,
    OrcamentoItemService,
)


def _edicao(**overrides) -> EditarOrcamentoItemSimplesData:
    base = dict(
        codigo="COPIA",
        item="Item copiado",
        descricao="Nova descricao",
        altura=Decimal("2500"),
        largura=Decimal("1000"),
        profundidade=Decimal("600"),
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("617.28"),
        tipo_item="MOVEL",
        preco_manual=False,
    )
    base.update(overrides)
    return EditarOrcamentoItemSimplesData(**base)


def test_duplicar_item_copia_relacoes_e_aplica_edicao(session: Session) -> None:
    versao, item = _criar_item_profundo(session)
    service = OrcamentoItemService(session)

    novo = service.duplicar_item(
        item.id, _edicao(codigo="RP_02", item="Roupeiro 8 portas", largura=Decimal("3000"))
    )

    # A brand-new item, in the SAME version, at the next order.
    assert novo.id != item.id
    assert novo.orcamento_versao_id == versao.id
    assert novo.ordem == item.ordem + 1
    # The edited dialog fields win over the cloned scalars.
    assert novo.codigo == "RP_02"
    assert novo.item == "Roupeiro 8 portas"
    assert novo.largura == Decimal("3000")
    assert novo.preco_total == Decimal("617.28")
    # Non-dialog scalars are inherited from the source (adjustment, production).
    assert novo.ajuste_eur == Decimal("2.50")
    assert novo.tipo_producao == "SERIE"

    # Children were copied, keyed to the new item.
    variaveis = _rows(session, OrcamentoItemVariavel, "item_id", novo.id)
    assert len(variaveis) == 1
    modulos = _rows(session, OrcamentoItemModulo, "orcamento_item_id", novo.id)
    assert len(modulos) == 1
    item_vsl = _rows(session, OrcamentoItemValuesetLinha, "orcamento_item_id", novo.id)
    assert len(item_vsl) == 1
    linhas = _rows(session, OrcamentoItemCusteioLinha, "orcamento_item_id", novo.id)
    assert len(linhas) == 2

    # The original is untouched.
    assert len(_rows(session, OrcamentoItemCusteioLinha, "orcamento_item_id", item.id)) == 2


def test_duplicar_item_remapeia_modulo_e_linha_pai(session: Session) -> None:
    _, item = _criar_item_profundo(session)
    service = OrcamentoItemService(session)

    novo = service.duplicar_item(item.id, _edicao())

    novo_modulo = _rows(session, OrcamentoItemModulo, "orcamento_item_id", novo.id)[0]
    novas_linhas = _rows(session, OrcamentoItemCusteioLinha, "orcamento_item_id", novo.id)
    novos_ids = {linha.id for linha in novas_linhas}

    # Costing line -> module reference points at the NEW module, not the source.
    origem_modulo = _rows(session, OrcamentoItemModulo, "orcamento_item_id", item.id)[0]
    com_modulo = [l for l in novas_linhas if l.orcamento_item_modulo_id is not None]
    assert com_modulo
    assert all(l.orcamento_item_modulo_id == novo_modulo.id for l in com_modulo)
    assert all(l.orcamento_item_modulo_id != origem_modulo.id for l in com_modulo)

    # Parent-line reference is remapped within the new item's own lines.
    com_pai = [l for l in novas_linhas if l.linha_pai_id is not None]
    assert com_pai
    assert all(l.linha_pai_id in novos_ids for l in com_pai)


def test_duplicar_item_copia_operacoes_das_linhas(session: Session) -> None:
    """The variant ops (ValueSet line) and per-line ops must travel with the copy.

    Without them, a later re-costing would drop the hardware mounting/CNC
    production costs — the exact regression reported on 260002_04.
    """
    _, item = _criar_item_profundo(session)
    service = OrcamentoItemService(session)

    novo = service.duplicar_item(item.id, _edicao())

    # ValueSet-line variant operations.
    novo_vsl_ids = _ids(session, OrcamentoItemValuesetLinha, "orcamento_item_id", novo.id)
    novas_vsl_ops = session.execute(
        select(OrcamentoItemValuesetLinhaOperacao).where(
            OrcamentoItemValuesetLinhaOperacao.orcamento_item_valueset_linha_id.in_(
                novo_vsl_ids
            )
        )
    ).scalars().all()
    assert len(novas_vsl_ops) == 1
    assert novas_vsl_ops[0].tempo_por_unidade_minutos == Decimal("3")

    # Per-line local operations.
    novo_linha_ids = _ids(session, OrcamentoItemCusteioLinha, "orcamento_item_id", novo.id)
    novas_linha_ops = session.execute(
        select(OrcamentoItemCusteioLinhaOperacao).where(
            OrcamentoItemCusteioLinhaOperacao.linha_id.in_(novo_linha_ids)
        )
    ).scalars().all()
    assert len(novas_linha_ops) == 1
    assert novas_linha_ops[0].codigo == "OP1"


def test_duplicar_item_mantem_origem_valueset_versao(session: Session) -> None:
    versao, item = _criar_item_profundo(session)
    origem_vsl = session.execute(
        select(OrcamentoValuesetLinha).where(
            OrcamentoValuesetLinha.orcamento_versao_id == versao.id
        )
    ).scalar_one()
    service = OrcamentoItemService(session)

    novo = service.duplicar_item(item.id, _edicao())

    # Version-level ValueSet lines are shared by the version (not copied), so
    # the new item's ValueSet lines keep the same origem references.
    nova_vsl = _rows(session, OrcamentoItemValuesetLinha, "orcamento_item_id", novo.id)[0]
    assert nova_vsl.origem_orcamento_valueset_linha_id == origem_vsl.id
    assert nova_vsl.origem_orcamento_versao_id == versao.id


def test_duplicar_item_inexistente_falha(session: Session) -> None:
    service = OrcamentoItemService(session)
    with pytest.raises(ValueError, match="item not found"):
        service.duplicar_item(999, _edicao())


def _criar_item_profundo(session: Session) -> tuple[OrcamentoVersao, OrcamentoItem]:
    cliente = Cliente(nome="Cliente Copia", is_temporary=True)
    session.add(cliente)
    session.flush()

    orcamento = Orcamento(ano=2026, num_orcamento="260002", cliente_id=cliente.id)
    session.add(orcamento)
    session.flush()

    versao = OrcamentoVersao(
        orcamento_id=orcamento.id,
        numero_versao=1,
        codigo_versao="260002_01",
        estado="Enviado",
        preco_total=Decimal("617.28"),
        tipo_producao_default="SERIE",
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

    item = OrcamentoItem(
        orcamento_versao_id=versao.id,
        ordem=1,
        codigo="IT-1",
        tipo_item="MOVEL",
        item="Item 1",
        descricao="Descricao 1",
        quantidade=Decimal("1"),
        unidade="un",
        preco_unitario=Decimal("617.28"),
        preco_total=Decimal("617.28"),
        ajuste_eur=Decimal("2.50"),
        tipo_producao="SERIE",
    )
    session.add(item)
    session.flush()

    session.add(
        OrcamentoItemVariavel(
            item_id=item.id, nome="LARGURA", valor=Decimal("800"), unidade="mm", ordem=1
        )
    )

    modulo = OrcamentoItemModulo(
        orcamento_item_id=item.id,
        ordem=1,
        nome="Modulo 1",
        descricao="Modulo teste",
        quantidade=Decimal("1"),
    )
    session.add(modulo)
    session.flush()

    item_vsl = OrcamentoItemValuesetLinha(
        orcamento_item_id=item.id,
        chave="FERRAGEM_PUXADOR",
        codigo_opcao="PUX-J",
        nome_opcao="Puxador J",
        padrao=True,
        ordem=1,
        origem_orcamento_valueset_linha_id=valueset_versao.id,
        origem_orcamento_versao_id=versao.id,
        herdado_do_orcamento=True,
        ativo=True,
    )
    session.add(item_vsl)
    session.flush()

    # The variant operation that carries the hardware mounting cost.
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
        descricao="Composto 1",
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
        descricao="Filho 1",
        nivel=1,
        ordem=2,
        quantidade=Decimal("2"),
        custo_mp=Decimal("20"),
        custo_total=Decimal("20"),
        preco_total=Decimal("30"),
        ativo=True,
    )
    session.add(filho)
    session.flush()

    # A locally edited per-line operation on the costing line.
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

    return versao, item


def _rows(session: Session, model, field: str, value: int):
    coluna = getattr(model, field)
    return list(session.execute(select(model).where(coluna == value)).scalars())


def _ids(session: Session, model, field: str, value: int) -> list[int]:
    return [row.id for row in _rows(session, model, field, value)]
