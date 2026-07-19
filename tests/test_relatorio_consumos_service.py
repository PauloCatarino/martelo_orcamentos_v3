"""Tests for the version consumption/cost report service (phase 8W.0)."""

from __future__ import annotations

from decimal import Decimal

import pytest

import app.models  # noqa: F401  (register all models on Base.metadata)
from app.models import OrcamentoItem, OrcamentoVersao
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaRepository,
)
from app.services.relatorio_consumos_service import RelatorioConsumosService


def _criar_versao(session, *, margem_lucro=Decimal("0")) -> int:
    versao = OrcamentoVersao(
        orcamento_id=1, numero_versao=1, codigo_versao="V1", estado="ATIVO",
        margem_lucro_pct=margem_lucro,
    )
    session.add(versao)
    session.flush()
    return versao.id


def _criar_item(
    session, versao_id, *, ordem, quantidade,
    altura=None, largura=None, profundidade=None,
) -> int:
    item = OrcamentoItem(
        orcamento_versao_id=versao_id, ordem=ordem, tipo_item="OUTRO",
        item=f"Item {ordem}", quantidade=Decimal(quantidade),
        altura=Decimal(altura) if altura is not None else None,
        largura=Decimal(largura) if largura is not None else None,
        profundidade=Decimal(profundidade) if profundidade is not None else None,
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
    assert placa.custo_mp_total == Decimal("25")    # m2 consumidos(5) x pliq(5)
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
    # Only the active line counts: m2 consumidos(1) x pliq(5) = 5.
    assert placa.custo_mp_total == Decimal("5")
    assert placa.m2_total_pecas == Decimal("1")


def test_resumo_versao_sem_linhas(session) -> None:
    versao_id = _criar_versao(session)
    _criar_item(session, versao_id, ordem=1, quantidade=1)
    session.commit()

    resumo = RelatorioConsumosService(session).resumo_da_versao(versao_id)

    assert resumo.placas == []
    assert resumo.orlas == []
    assert resumo.ferragens == []
    assert resumo.distribuicao.custo_produzido == Decimal("0")
    # The five machine centres always exist (with zero cost).
    assert len(resumo.maquinas) == 5
    assert resumo.operacoes == []


def test_resumo_expoe_operacao_e_maquina_efetivas(session) -> None:
    versao_id = _criar_versao(session)
    item = _criar_item(session, versao_id, ordem=1, quantidade=2)
    _linha_placa(
        session,
        item,
        quantidade=Decimal("10"),
        operacoes="CNC_ABD",
        maquina="CNC_ABD",
        tempo_setup=Decimal("0.01"),
        tempo_cnc=Decimal("0.10"),
        custo_cnc=Decimal("0.055"),
        custo_producao=Decimal("0.055"),
    )
    session.commit()

    resumo = RelatorioConsumosService(session).resumo_da_versao(versao_id)

    (operacao,) = resumo.operacoes
    assert operacao.operacoes == "CNC_ABD"
    assert operacao.maquina == "CNC_ABD"
    assert operacao.qt_total == Decimal("20")
    assert operacao.tempo_setup == Decimal("0.02")
    assert operacao.tempo_cnc == Decimal("0.20")
    assert operacao.custo_total == Decimal("0.110")


# --- Phase 8W.1.1: recompute-before-aggregate + Excluir semantics ------------


def _linha_por_custear(session, item_id):
    """A line with measure FORMULAS and material but NOT yet costed (area/cost
    are computed only by the pipeline)."""
    return OrcamentoItemCusteioLinhaRepository(session).create_linha(
        orcamento_item_id=item_id, tipo_linha="PECA", descricao="Lateral",
        unidade="m2", quantidade=Decimal("1"),
        comp="H", larg="P", esp_mp=Decimal("19"),
        preco_liquido=Decimal("5"), desperdicio_percentagem=Decimal("0"),
        ref_le="LE01", descricao_no_orcamento="AGL", nivel=0, ativo=True,
    )


def test_atualizar_recalcula_antes_de_agregar(session) -> None:
    versao_id = _criar_versao(session)
    item = _criar_item(
        session, versao_id, ordem=1, quantidade=1,
        altura="2000", largura="1000", profundidade="500",
    )
    _linha_por_custear(session, item)
    session.commit()
    service = RelatorioConsumosService(session)

    # Before recompute: the line has no area/cost -> nothing aggregated.
    antes = service.resumo_da_versao(versao_id)
    assert antes.placas == [] or antes.placas[0].m2_total_pecas == Decimal("0")

    # The report's Atualizar recomputes the costing of every item first.
    service.recalcular_versao(versao_id)
    depois = service.resumo_da_versao(versao_id)

    (placa,) = depois.placas
    assert placa.m2_total_pecas == Decimal("1")     # H=2000 x P=500 -> 1 m2
    assert placa.custo_mp_total == Decimal("5")     # 1 m2 x 5 €
    assert depois.distribuicao.custo_produzido == Decimal("5")


def test_excluir_nao_muda_consumo_mas_baixa_distribuicao_e_total(session) -> None:
    versao_id = _criar_versao(session)
    item = _criar_item(
        session, versao_id, ordem=1, quantidade=1,
        altura="2000", largura="1000", profundidade="500",
    )
    linha = _linha_por_custear(session, item)
    session.commit()
    service = RelatorioConsumosService(session)

    service.recalcular_versao(versao_id)
    base = service.resumo_da_versao(versao_id)
    consumo_base = base.placas[0].m2_total_pecas
    custo_base = base.placas[0].custo_mp_total
    placas_dist_base = next(
        c.euros for c in base.distribuicao.categorias if c.nome == "Placas"
    )
    venda_base = base.distribuicao.total_venda
    assert placas_dist_base == Decimal("5") and venda_base == Decimal("5")

    # Exclude the raw material on the line and re-aggregate.
    OrcamentoItemCusteioLinhaRepository(session).update_linha(
        id=linha.id, excluir_mp=True
    )
    session.commit()
    service.recalcular_versao(versao_id)
    com_excluir = service.resumo_da_versao(versao_id)

    # Consumption is unchanged (physical, for purchasing)...
    assert com_excluir.placas[0].m2_total_pecas == consumo_base
    assert com_excluir.placas[0].custo_mp_total == custo_base
    # ...but the distribution and the sell total drop (the cost is excluded).
    placas_dist = next(
        c.euros for c in com_excluir.distribuicao.categorias if c.nome == "Placas"
    )
    assert placas_dist == Decimal("0")
    assert com_excluir.distribuicao.total_venda == Decimal("0")


def test_editar_medida_reflete_no_consumo(session) -> None:
    versao_id = _criar_versao(session)
    item = _criar_item(
        session, versao_id, ordem=1, quantidade=1,
        altura="2000", largura="1000", profundidade="500",
    )
    linha = _linha_por_custear(session, item)
    session.commit()
    service = RelatorioConsumosService(session)

    service.recalcular_versao(versao_id)
    assert service.resumo_da_versao(versao_id).placas[0].m2_total_pecas == Decimal("1")

    # Change the width formula H x L (instead of H x P) -> 2000 x 1000 = 2 m2.
    OrcamentoItemCusteioLinhaRepository(session).update_linha(id=linha.id, larg="L")
    session.commit()
    service.recalcular_versao(versao_id)

    assert service.resumo_da_versao(versao_id).placas[0].m2_total_pecas == Decimal("2")


# --- Phase 8W.2: Não-Stock boards --------------------------------------------


def _linha_placa_real(session, item_id, **kw):
    """A board line with measure FORMULAS + material + board dimensions, so the
    pipeline computes area/cost (board cost >> %-waste cost here)."""
    base = dict(
        orcamento_item_id=item_id, tipo_linha="PECA", descricao="Lateral",
        unidade="m2", quantidade=Decimal("1"), comp="H", larg="P",
        comp_mp=Decimal("2750"), larg_mp=Decimal("1830"), esp_mp=Decimal("19"),
        preco_liquido=Decimal("5"), desperdicio_percentagem=Decimal("0"),
        ref_le="LE01", descricao_no_orcamento="AGL", nivel=0, ativo=True,
    )
    base.update(kw)
    return OrcamentoItemCusteioLinhaRepository(session).create_linha(**base)


def test_nao_stock_usa_custo_de_placa_inteira_no_total(session) -> None:
    versao_id = _criar_versao(session)
    item = _criar_item(
        session, versao_id, ordem=1, quantidade=1,
        altura="2000", largura="1000", profundidade="500",
    )
    _linha_placa_real(session, item)
    session.commit()
    service = RelatorioConsumosService(session)

    service.recalcular_versao(versao_id)
    base = service.resumo_da_versao(versao_id)
    placa = base.placas[0]
    assert placa.nao_stock is False
    assert placa.custo_mp_total == Decimal("5")            # theoretical %-waste
    assert placa.custo_placa_inteira == Decimal("25.1625")  # whole board
    assert placa.custo_no_orcamento == Decimal("5")
    assert base.distribuicao.total_venda == Decimal("5")

    # Mark the board Não-Stock and recompute.
    service.guardar_nao_stock(versao_id, [("LE01", "AGL", Decimal("19"), True)])
    service.recalcular_versao(versao_id)
    com = service.resumo_da_versao(versao_id)
    placa2 = com.placas[0]

    assert placa2.nao_stock is True
    assert placa2.custo_no_orcamento == Decimal("25.1625")     # whole board
    assert placa2.agravamento == Decimal("20.1625")
    # The physical consumption is unchanged (only the budget cost changed).
    assert placa2.m2_total_pecas == placa.m2_total_pecas
    assert placa2.qt_placas == placa.qt_placas
    assert placa2.custo_mp_total == Decimal("5")               # theoretical kept
    # The budget total now uses the whole-board cost.
    assert com.distribuicao.total_venda == Decimal("25.1625")
    placas_dist = next(
        c.euros for c in com.distribuicao.categorias if c.nome == "Placas"
    )
    assert placas_dist == Decimal("25.1625")

    # Unmark -> back to the %-waste cost.
    service.guardar_nao_stock(versao_id, [("LE01", "AGL", Decimal("19"), False)])
    service.recalcular_versao(versao_id)
    de_volta = service.resumo_da_versao(versao_id)
    assert de_volta.placas[0].nao_stock is False
    assert de_volta.placas[0].custo_no_orcamento == Decimal("5")
    assert de_volta.distribuicao.total_venda == Decimal("5")


def test_nao_stock_persiste_e_sobrevive_a_recalculo(session) -> None:
    versao_id = _criar_versao(session)
    item = _criar_item(
        session, versao_id, ordem=1, quantidade=1,
        altura="2000", largura="1000", profundidade="500",
    )
    _linha_placa_real(session, item)
    session.commit()
    service = RelatorioConsumosService(session)

    service.guardar_nao_stock(versao_id, [("LE01", "AGL", Decimal("19"), True)])

    # Stored and listed.
    rows = service.listar_nao_stock(versao_id)
    assert [(r.ref_le, r.nao_stock) for r in rows] == [("LE01", True)]

    # Recomputing the costing does NOT lose the Não-Stock state.
    service.recalcular_versao(versao_id)
    service.recalcular_versao(versao_id)
    assert service.resumo_da_versao(versao_id).placas[0].nao_stock is True


# --- Phase 8W.2.1: whole-board waste recalculated and propagated --------------


def _ler_linha(session, linha_id):
    return OrcamentoItemCusteioLinhaRepository(session).get_by_id(linha_id)


def test_placa_inteira_ajusta_desp_global_e_propaga(session) -> None:
    """m²peças=2, área=5.985, desp orig 15% -> qt_placas=1 -> desp_global≈199.25%;
    propagated to all the board's lines, whose cost sums to the whole-board cost."""
    versao_id = _criar_versao(session)
    item = _criar_item(
        session, versao_id, ordem=1, quantidade=1,
        altura="1000", largura="1000", profundidade="1000",
    )
    # Two lines of the SAME board: each 1 m² (H x P = 1.0 x 1.0), so m²peças = 2.
    comum = dict(
        comp_mp=Decimal("2850"), larg_mp=Decimal("2100"), esp_mp=Decimal("19"),
        preco_liquido=Decimal("10"), desperdicio_percentagem=Decimal("15"),
    )
    l1 = _linha_placa_real(session, item, comp="H", larg="P", **comum)
    l2 = _linha_placa_real(session, item, comp="H", larg="P", **comum)
    session.commit()
    service = RelatorioConsumosService(session)

    service.guardar_nao_stock(versao_id, [("LE01", "AGL", Decimal("19"), True)])
    service.recalcular_versao(versao_id)

    # The global waste % is stored on every line; the original (15%) is saved.
    for linha_id in (l1.id, l2.id):
        linha = _ler_linha(session, linha_id)
        assert linha.desperdicio_percentagem == Decimal("199.25")
        assert linha.desperdicio_percentagem_original == Decimal("15")
        # area(1) x qt(1) x pliq(10) x (1 + 1.9925) = 29.925
        assert linha.custo_mp == Decimal("29.925")

    # Report: theoretical kept on the ORIGINAL waste, budget = whole board.
    placa = service.resumo_da_versao(versao_id).placas[0]
    assert placa.qt_placas == 1
    assert placa.area_placa == Decimal("5.985")
    assert placa.custo_placa_inteira == Decimal("59.85")        # 1 x 5.985 x 10
    assert placa.custo_mp_total == Decimal("23.00")             # 2 x 1.15 x 10
    assert placa.custo_no_orcamento == Decimal("59.85")
    assert placa.agravamento == Decimal("36.85")                # 59.85 - 23
    # The budget sell total (no margins) equals the whole-board cost.
    assert service.resumo_da_versao(versao_id).distribuicao.total_venda == Decimal(
        "59.85"
    )


def test_placa_inteira_desligar_repoe_desp_original(session) -> None:
    versao_id = _criar_versao(session)
    item = _criar_item(
        session, versao_id, ordem=1, quantidade=1,
        altura="1000", largura="1000", profundidade="1000",
    )
    linha = _linha_placa_real(
        session, item, comp="H", larg="P",
        comp_mp=Decimal("2850"), larg_mp=Decimal("2100"),
        preco_liquido=Decimal("10"), desperdicio_percentagem=Decimal("15"),
    )
    session.commit()
    service = RelatorioConsumosService(session)

    service.guardar_nao_stock(versao_id, [("LE01", "AGL", Decimal("19"), True)])
    service.recalcular_versao(versao_id)
    assert _ler_linha(session, linha.id).desperdicio_percentagem_original == Decimal(
        "15"
    )

    # Unmark -> the original 15% is restored and the saved value is cleared.
    service.guardar_nao_stock(versao_id, [("LE01", "AGL", Decimal("19"), False)])
    service.recalcular_versao(versao_id)

    restaurada = _ler_linha(session, linha.id)
    assert restaurada.desperdicio_percentagem == Decimal("15")
    assert restaurada.desperdicio_percentagem_original is None
    # area(1) x qt(1) x pliq(10) x 1.15 = 11.5
    assert restaurada.custo_mp == Decimal("11.5")


def test_placa_inteira_recalculo_mantem_coerencia_ao_adicionar_pecas(session) -> None:
    versao_id = _criar_versao(session)
    item = _criar_item(
        session, versao_id, ordem=1, quantidade=1,
        altura="1000", largura="1000", profundidade="1000",
    )
    comum = dict(
        comp="H", larg="P", comp_mp=Decimal("2850"), larg_mp=Decimal("2100"),
        preco_liquido=Decimal("10"), desperdicio_percentagem=Decimal("15"),
    )
    _linha_placa_real(session, item, **comum)
    session.commit()
    service = RelatorioConsumosService(session)

    service.guardar_nao_stock(versao_id, [("LE01", "AGL", Decimal("19"), True)])
    service.recalcular_versao(versao_id)
    uma = service.resumo_da_versao(versao_id).placas[0]
    assert uma.qt_placas == 1
    assert uma.custo_no_orcamento == Decimal("59.85")    # 1 board x 5.985 x 10

    # Add a second piece (m²peças 1 -> 2). qt_placas/desp_global are recomputed.
    _linha_placa_real(session, item, **comum)
    session.commit()
    service.recalcular_versao(versao_id)

    duas = service.resumo_da_versao(versao_id).placas[0]
    assert duas.m2_total_pecas == Decimal("2")
    assert duas.qt_placas == 1                            # still 1 whole board
    assert duas.custo_no_orcamento == Decimal("59.85")   # whole-board cost unchanged
    assert duas.custo_placa_inteira == Decimal("59.85")


def test_placa_inteira_ignora_sem_pecas_e_sem_dimensoes(session) -> None:
    # Item A has NO measures, so its H x P line computes area 0 (no pieces),
    # even though the board has dimensions.
    versao_id = _criar_versao(session)
    item_a = _criar_item(session, versao_id, ordem=1, quantidade=1)
    sem_pecas = _linha_placa_real(
        session, item_a, comp="H", larg="P",
        comp_mp=Decimal("2850"), larg_mp=Decimal("2100"), esp_mp=Decimal("19"),
        desperdicio_percentagem=Decimal("15"),
    )
    # Item B has measures (1 m² pieces) but its line has NO board dimensions.
    item_b = _criar_item(
        session, versao_id, ordem=2, quantidade=1,
        altura="1000", largura="1000", profundidade="1000",
    )
    sem_dimensoes = _linha_placa_real(
        session, item_b, comp="H", larg="P",
        comp_mp=None, larg_mp=None, esp_mp=Decimal("25"),
        descricao_no_orcamento="AGL25", desperdicio_percentagem=Decimal("15"),
    )
    session.commit()
    service = RelatorioConsumosService(session)

    service.guardar_nao_stock(
        versao_id,
        [
            ("LE01", "AGL", Decimal("19"), True),
            ("LE01", "AGL25", Decimal("25"), True),
        ],
    )
    service.recalcular_versao(versao_id)

    # Neither board was adjusted: no original was saved, waste stays the material's.
    for linha_id in (sem_pecas.id, sem_dimensoes.id):
        linha = _ler_linha(session, linha_id)
        assert linha.desperdicio_percentagem_original is None
        assert linha.desperdicio_percentagem == Decimal("15")
