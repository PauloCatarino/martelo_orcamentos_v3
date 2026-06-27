"""Tests for production dashboard aggregates."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace


def _processo(**overrides) -> SimpleNamespace:
    base = {
        "id": 1,
        "codigo_processo": "26.1028_01_01",
        "num_enc_phc": "1028",
        "nome_cliente": "Cliente Alfa",
        "nome_cliente_simplex": "cliente alfa",
        "ref_cliente": "REF-A",
        "obra": "Cozinha Lisboa",
        "localizacao": "Lisboa",
        "num_orcamento": "260001",
        "responsavel": "Ana",
        "descricao_producao": "Moveis lacados",
        "estado": "Desenho",
        "data_entrega": "01-06-2026",
        "preco_total": Decimal("100.00"),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_calcular_dashboard_agrega_kpis(monkeypatch) -> None:
    import app.services.producao_dashboard_service as module

    processos = [
        _processo(),
        _processo(
            id=2,
            estado="Produ\u00e7\u00e3o",
            responsavel="Bruno",
            nome_cliente="Cliente Beta",
            data_entrega="10-07-2026",
            preco_total=Decimal("250.40"),
        ),
        _processo(
            id=3,
            estado="Finalizado",
            responsavel="Ana",
            nome_cliente="Cliente Alfa",
            data_entrega="01-01-2026",
            preco_total=Decimal("999.00"),
        ),
        _processo(
            id=4,
            estado="Arquivado",
            responsavel="",
            nome_cliente="",
            data_entrega="01-01-2026",
            preco_total=None,
        ),
        _processo(
            id=5,
            estado="Desenho",
            responsavel="Ana",
            nome_cliente="Cliente Alfa",
            data_entrega="01-06-2026",
            preco_total=None,
        ),
        _processo(
            id=6,
            estado="Desenho",
            responsavel="Ana",
            nome_cliente="Cliente Alfa",
            data_entrega="01-01-1900",
            preco_total=Decimal("0.00"),
        ),
    ]

    class FakeProducaoService:
        def __init__(self, session):
            self.session = session

        def listar_processos(self):
            return processos

    monkeypatch.setattr(module, "ProducaoService", FakeProducaoService)

    dados = module.calcular_dashboard(object(), hoje=date(2026, 6, 27))

    assert dados.total == 6
    assert dados.em_desenho == 3
    assert dados.em_producao == 1
    assert dados.finalizadas == 1
    assert dados.arquivadas == 1
    assert dados.atrasadas == 2
    assert dados.sem_preco == 1
    assert dados.valor_aberto == 350.40
    assert dados.por_responsavel[0] == ("Ana", 4)
    assert dados.por_cliente[0] == ("Cliente Alfa", 4)
    assert [row["dias_atraso"] for row in dados.lista_atrasadas] == [26, 26]
    assert dados.lista_atrasadas[0] == {
        "id": 1,
        "codigo": "26.1028_01_01",
        "cliente": "Cliente Alfa",
        "responsavel": "Ana",
        "data_entrega": "01-06-2026",
        "dias_atraso": 26,
    }


def test_calcular_dashboard_aplica_filtros(monkeypatch) -> None:
    import app.services.producao_dashboard_service as module

    processos = [
        _processo(nome_cliente="Cliente Alfa", responsavel="Ana"),
        _processo(nome_cliente="Cliente Beta", responsavel="Bruno"),
    ]

    class FakeProducaoService:
        def __init__(self, session):
            self.session = session

        def listar_processos(self):
            return processos

    monkeypatch.setattr(module, "ProducaoService", FakeProducaoService)

    dados = module.calcular_dashboard(
        object(),
        cliente="Cliente Beta",
        utilizador="Bruno",
        hoje=date(2026, 6, 27),
    )

    assert dados.total == 1
    assert dados.por_cliente == [("Cliente Beta", 1)]
    assert dados.lista_atrasadas == [
        {
            "id": 1,
            "codigo": "26.1028_01_01",
            "cliente": "Cliente Beta",
            "responsavel": "Bruno",
            "data_entrega": "01-06-2026",
            "dias_atraso": 26,
        }
    ]
