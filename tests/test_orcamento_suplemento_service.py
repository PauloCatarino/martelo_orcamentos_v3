"""Tests for budget-level non-stock board supplements."""

from __future__ import annotations

from decimal import Decimal

from app.domain.precos import MargensOrcamento
from app.models import DefMateriaPrima, OrcamentoItem, OrcamentoItemCusteioLinha
from app.repositories.orcamento_versao_placa_nao_stock_repository import (
    OrcamentoVersaoPlacaNaoStockRepository,
)
from app.services.orcamento_item_service import OrcamentoItemService
from app.services.orcamento_suplemento_service import (
    GuardarSuplementoPlacaData,
    OrcamentoSuplementoService,
)


def _adicionar_materia_suplemento(session, preco: str = "70") -> None:
    session.add(
        DefMateriaPrima(
            ref_le="PLC0120",
            descricao="SUPLEMENTO (CUSTO ADICIONAL NÃO PROGRAMADO)",
            familia_martelo="PLACAS",
            unidade="UND",
            preco_liquido=Decimal(preco),
            ativo=True,
        )
    )
    session.flush()


def _adicionar_placa(session, item_id: int, ref_le: str, descricao: str) -> None:
    session.add(
        OrcamentoItemCusteioLinha(
            orcamento_item_id=item_id,
            tipo_linha="PECA",
            descricao="Painel",
            ref_le=ref_le,
            descricao_no_orcamento=descricao,
            familia_materia_prima="PLACAS",
            esp_mp=Decimal("19"),
            quantidade=Decimal("1"),
            ativo=True,
        )
    )


def test_listar_agrega_mesma_referencia_usada_em_varios_items(session) -> None:
    _adicionar_materia_suplemento(session)
    for item_id in (1, 2):
        session.add(
            OrcamentoItem(
                id=item_id,
                orcamento_versao_id=10,
                ordem=item_id,
                item=f"Item {item_id}",
                quantidade=Decimal("1"),
            )
        )
        descricao = "ROBLE DAFNE 19" if item_id == 1 else "Roble Dafne (local)"
        _adicionar_placa(session, item_id, "PLC1000", descricao)
    session.commit()

    rows = OrcamentoSuplementoService(session).listar(10)

    assert len(rows) == 1
    assert rows[0].numero_itens == 2
    assert rows[0].valor_base == Decimal("70")
    assert rows[0].ativo is False


def test_desativar_por_referencia_abrange_descricao_anterior(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)
    repo.set_suplemento(
        10,
        "PLC1000",
        "Descrição anterior",
        Decimal("19"),
        ativo=True,
        suplemento_ref_le="PLC0120",
        valor_base=Decimal("70"),
        valor_local=Decimal("70"),
    )

    repo.set_suplemento(
        10,
        "PLC1000",
        "Descrição atual",
        Decimal("19"),
        ativo=False,
    )

    assert not any(row.suplemento_ativo for row in repo.list_by_versao(10))


def test_guardar_duas_referencias_e_editar_valor_local(session) -> None:
    _adicionar_materia_suplemento(session)
    service = OrcamentoSuplementoService(session)

    ativos = service.guardar(
        10,
        [
            GuardarSuplementoPlacaData(
                "PLC1000", "ROBLE DAFNE 19", Decimal("19"), True, Decimal("70")
            ),
            GuardarSuplementoPlacaData(
                "PLC2000",
                "ROBLE AZABACHE 19",
                Decimal("19"),
                True,
                Decimal("82.50"),
                "Encomenda especial à fábrica.",
                Decimal("2"),
            ),
        ],
    )

    rows = OrcamentoVersaoPlacaNaoStockRepository(session).list_by_versao(10)
    assert ativos == 2
    assert sum(row.suplemento_valor_local for row in rows) == Decimal("152.50")
    assert rows[0].suplemento_ref_le == "PLC0120"
    assert [row.suplemento_editado_localmente for row in rows] == [False, True]
    assert rows[1].suplemento_nota_cliente == "Encomenda especial à fábrica."
    assert rows[1].suplemento_quantidade == Decimal("2")


def test_preco_suplemento_e_fixo_sem_qualquer_margem(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)
    for ref_le, descricao in (
        ("PLC1000", "ROBLE DAFNE 19"),
        ("PLC2000", "ROBLE AZABACHE 19"),
    ):
        repo.set_suplemento(
            10,
            ref_le,
            descricao,
            Decimal("19"),
            ativo=True,
            suplemento_ref_le="PLC0120",
            valor_base=Decimal("70"),
            valor_local=Decimal("70"),
        )
    service = OrcamentoItemService(session)
    service.get_margens_versao = lambda _versao_id: MargensOrcamento(
        margem_mp_pct=Decimal("15"),
        margem_mao_obra_pct=Decimal("99"),
        margem_acabamentos_pct=Decimal("99"),
        custos_administrativos_pct=Decimal("5"),
        margem_lucro_pct=Decimal("10"),
    )

    # All budget margins are deliberately ignored for extraordinary charges.
    assert service.get_custo_suplementos_versao(10) == Decimal("140")
    assert service.get_preco_suplementos_versao(10) == Decimal("140.00")


def test_gera_uma_linha_automatica_por_suplemento(session) -> None:
    repo = OrcamentoVersaoPlacaNaoStockRepository(session)
    for ref_le, descricao, nota, quantidade in (
        ("PLC1000", "ROBLE DAFNE 19", "Fora de stock.", Decimal("1")),
        ("PLC2000", "ROBLE AZABACHE 19", "Encomenda especial.", Decimal("2")),
    ):
        repo.set_suplemento(
            10,
            ref_le,
            descricao,
            Decimal("19"),
            ativo=True,
            suplemento_ref_le="PLC0120",
            valor_base=Decimal("70"),
            valor_local=Decimal("70"),
            nota_cliente=nota,
            quantidade=quantidade,
        )
    service = OrcamentoItemService(session)

    items = service.list_items_com_suplementos_by_versao(10)

    assert len(items) == 2
    assert [item.codigo for item in items] == ["SUP_NSTOCK", "SUP_NSTOCK"]
    assert [item.tipo_item for item in items] == ["SUPLEMENTO", "SUPLEMENTO"]
    assert [item.quantidade for item in items] == [Decimal("1"), Decimal("2")]
    assert all(item.unidade == "un" for item in items)
    assert [item.preco_unitario for item in items] == [Decimal("70.00"), Decimal("70.00")]
    assert [item.preco_total for item in items] == [Decimal("70.00"), Decimal("140.00")]
    assert "PLC1000" in items[0].descricao
    assert "Fora de stock." in items[0].descricao
    assert sum(item.preco_total for item in items) == service.get_preco_suplementos_versao(10)
    assert all(item.id < 0 for item in items)
