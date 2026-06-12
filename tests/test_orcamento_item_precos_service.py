"""Tests for the margins/price workflows of the Orcamento item service."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from types import SimpleNamespace

from app.domain.precos import MargensOrcamento
from app.repositories.orcamento_item_repository import OrcamentoItemResumo
from app.services import orcamento_item_service as service_module
from app.services.orcamento_item_service import OrcamentoItemService

_MARGENS_EXEMPLO = MargensOrcamento(
    margem_lucro_pct=Decimal("10"),
    margem_mp_pct=Decimal("15"),
    margem_mao_obra_pct=Decimal("5"),
    margem_acabamentos_pct=Decimal("5"),
    custos_administrativos_pct=Decimal("3"),
)


def _item(
    item_id: int,
    quantidade: Decimal = Decimal("1"),
    preco_unitario: Decimal | None = None,
    preco_total: Decimal | None = None,
    ajuste_eur: Decimal = Decimal("0"),
) -> OrcamentoItemResumo:
    return OrcamentoItemResumo(
        id=item_id,
        orcamento_versao_id=7,
        ordem=item_id,
        codigo=None,
        item=f"Item {item_id}",
        descricao=None,
        altura=None,
        largura=None,
        profundidade=None,
        quantidade=quantidade,
        unidade="un",
        preco_unitario=preco_unitario,
        preco_total=preco_total,
        ajuste_eur=ajuste_eur,
    )


def _linha(
    orcamento_item_id: int,
    *,
    tipo_linha: str = "PECA",
    ativo: bool = True,
    custo_mp=None,
    custo_orlas=None,
    custo_ferragem=None,
    custo_acabamento=None,
    custo_producao=None,
    custo_corte=None,
    custo_orlagem=None,
    custo_cnc=None,
    custo_montagem_manual=None,
    fator_serie=None,
    excluir_mp: bool = False,
    excluir_orla: bool = False,
    excluir_ferragem: bool = False,
    excluir_acabamento: bool = False,
    excluir_producao: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        orcamento_item_id=orcamento_item_id,
        tipo_linha=tipo_linha,
        ativo=ativo,
        custo_mp=custo_mp,
        custo_orlas=custo_orlas,
        custo_ferragem=custo_ferragem,
        custo_acabamento=custo_acabamento,
        custo_producao=custo_producao,
        custo_corte=custo_corte,
        custo_orlagem=custo_orlagem,
        custo_cnc=custo_cnc,
        custo_montagem_manual=custo_montagem_manual,
        fator_serie=fator_serie,
        excluir_mp=excluir_mp,
        excluir_orla=excluir_orla,
        excluir_ferragem=excluir_ferragem,
        excluir_acabamento=excluir_acabamento,
        excluir_producao=excluir_producao,
    )


class _FakeItemRepository:
    items: list[OrcamentoItemResumo] = []
    margens = MargensOrcamento()
    updated_margens: tuple[int, MargensOrcamento] | None = None
    updated_ajuste: tuple[int, Decimal] | None = None
    updated_precos: dict[int, tuple[Decimal, Decimal]] = {}
    sum_total = Decimal("0")
    updated_versao_total: tuple[int, Decimal] | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_items_by_versao(self, orcamento_versao_id: int) -> list[OrcamentoItemResumo]:
        return self.items

    def get_item_by_id(self, item_id: int) -> OrcamentoItemResumo | None:
        return next((item for item in self.items if item.id == item_id), None)

    def get_margens_versao(self, orcamento_versao_id: int) -> MargensOrcamento | None:
        return self.margens

    def update_margens_versao(
        self, orcamento_versao_id: int, margens: MargensOrcamento
    ) -> bool:
        self.__class__.updated_margens = (orcamento_versao_id, margens)
        self.__class__.margens = margens
        return True

    def update_ajuste_item(self, item_id: int, ajuste_eur: Decimal) -> bool:
        self.__class__.updated_ajuste = (item_id, ajuste_eur)
        self.__class__.items = [
            replace(item, ajuste_eur=ajuste_eur) if item.id == item_id else item
            for item in self.items
        ]
        return True

    def update_preco_item(
        self, item_id: int, preco_unitario: Decimal, preco_total: Decimal
    ) -> bool:
        self.__class__.updated_precos[item_id] = (preco_unitario, preco_total)
        return True

    def sum_preco_total_by_versao(self, orcamento_versao_id: int) -> Decimal:
        return self.sum_total

    def update_preco_total_versao(
        self, orcamento_versao_id: int, preco_total: Decimal
    ) -> bool:
        self.__class__.updated_versao_total = (orcamento_versao_id, preco_total)
        return True


class _FakeCusteioRepository:
    linhas: list[SimpleNamespace] = []
    chamadas: list[str] = []

    def __init__(self, _session: object) -> None:
        pass

    def list_by_orcamento_versao(self, orcamento_versao_id: int) -> list[SimpleNamespace]:
        self.__class__.chamadas.append("list_by_orcamento_versao")
        return self.linhas

    def list_active_by_orcamento_item(self, orcamento_item_id: int) -> list[SimpleNamespace]:
        self.__class__.chamadas.append("list_active_by_orcamento_item")
        return [
            linha
            for linha in self.linhas
            if linha.orcamento_item_id == orcamento_item_id and linha.ativo
        ]


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _make_service(monkeypatch) -> tuple[OrcamentoItemService, _FakeSession]:
    _FakeItemRepository.updated_margens = None
    _FakeItemRepository.updated_ajuste = None
    _FakeItemRepository.updated_precos = {}
    _FakeItemRepository.updated_versao_total = None
    _FakeCusteioRepository.chamadas = []
    monkeypatch.setattr(service_module, "OrcamentoItemRepository", _FakeItemRepository)
    monkeypatch.setattr(
        service_module, "OrcamentoItemCusteioLinhaRepository", _FakeCusteioRepository
    )
    session = _FakeSession()
    return OrcamentoItemService(session), session


def test_aplicar_precos_substitui_preco_e_mantem_manual(monkeypatch) -> None:
    """Items with cost lines get the computed price; manual items keep theirs."""
    _FakeItemRepository.items = [
        _item(1, quantidade=Decimal("2"), preco_unitario=Decimal("99")),
        _item(2, preco_unitario=Decimal("10"), preco_total=Decimal("10")),
    ]
    _FakeItemRepository.margens = _MARGENS_EXEMPLO
    _FakeItemRepository.sum_total = Decimal("460.93")
    _FakeCusteioRepository.linhas = [
        _linha(
            1,
            custo_mp=Decimal("100"),
            custo_acabamento=Decimal("30"),
            custo_producao=Decimal("50"),
        ),
    ]
    service, session = _make_service(monkeypatch)

    resultado = service.aplicar_precos_da_versao(7)

    # Spec example: 199.00 x 1.03 x 1.10 = 225.467 -> 225.47; qt 2 -> 450.93.
    assert _FakeItemRepository.updated_precos == {
        1: (Decimal("225.47"), Decimal("450.93"))
    }
    assert resultado.itens_atualizados == 1
    assert resultado.itens_sem_custeio == 1
    assert resultado.soma_preco_total == Decimal("460.93")
    assert _FakeItemRepository.updated_versao_total == (7, Decimal("460.93"))
    assert session.committed is True


def test_aplicar_precos_respeita_exclusoes_e_linhas_inativas(monkeypatch) -> None:
    """Excluded costs and inactive/division lines stay out of the blocks."""
    _FakeItemRepository.items = [_item(1)]
    _FakeItemRepository.margens = MargensOrcamento()  # zeros: price == cost
    _FakeCusteioRepository.linhas = [
        _linha(
            1,
            custo_mp=Decimal("100"),
            custo_acabamento=Decimal("30"),
            custo_producao=Decimal("50"),
            excluir_producao=True,
        ),
        _linha(1, ativo=False, custo_mp=Decimal("999")),
        _linha(1, tipo_linha="DIVISAO_INDEPENDENTE", custo_mp=Decimal("999")),
    ]
    service, _session = _make_service(monkeypatch)

    service.aplicar_precos_da_versao(7)

    # 100 (MP) + 30 (acabamento); the excluded producao does NOT enter.
    assert _FakeItemRepository.updated_precos == {
        1: (Decimal("130.00"), Decimal("130.00"))
    }


def test_definir_ajuste_item_reaplica_preco(monkeypatch) -> None:
    _FakeItemRepository.items = [_item(1)]
    _FakeItemRepository.margens = MargensOrcamento()
    _FakeCusteioRepository.linhas = [_linha(1, custo_mp=Decimal("100"))]
    service, session = _make_service(monkeypatch)

    service.definir_ajuste_item(1, Decimal("-10"))

    assert _FakeItemRepository.updated_ajuste == (1, Decimal("-10"))
    assert _FakeItemRepository.updated_precos == {
        1: (Decimal("90.00"), Decimal("90.00"))
    }
    assert session.committed is True


def test_definir_ajuste_item_sem_custeio_mantem_preco_manual(monkeypatch) -> None:
    _FakeItemRepository.items = [_item(1, preco_unitario=Decimal("10"))]
    _FakeCusteioRepository.linhas = []
    service, session = _make_service(monkeypatch)

    service.definir_ajuste_item(1, Decimal("5"))

    assert _FakeItemRepository.updated_ajuste == (1, Decimal("5"))
    assert _FakeItemRepository.updated_precos == {}  # manual price untouched
    assert session.committed is True


def test_definir_margens_reaplica_formula_sem_recalcular_custeios(monkeypatch) -> None:
    _FakeItemRepository.items = [_item(1)]
    _FakeCusteioRepository.linhas = [_linha(1, custo_mp=Decimal("100"))]
    service, _session = _make_service(monkeypatch)

    margens = MargensOrcamento(margem_mp_pct=Decimal("15"))
    service.definir_margens_versao(7, margens)

    assert _FakeItemRepository.updated_margens == (7, margens)
    assert _FakeItemRepository.updated_precos == {
        1: (Decimal("115.00"), Decimal("115.00"))
    }
    # Only line READS happened: the costing pipeline was not re-run.
    assert set(_FakeCusteioRepository.chamadas) == {"list_by_orcamento_versao"}


def test_get_margens_versao_devolve_zeros_quando_nao_ha_versao(monkeypatch) -> None:
    _FakeItemRepository.margens = None
    service, _session = _make_service(monkeypatch)

    assert service.get_margens_versao(99) == MargensOrcamento()


def test_recalcular_preco_item_calcula_grava_e_devolve(monkeypatch) -> None:
    """One item is re-priced from its lines; result mirrors the stored price."""
    _FakeItemRepository.items = [
        _item(1, quantidade=Decimal("2"), preco_unitario=Decimal("99")),
    ]
    _FakeItemRepository.margens = _MARGENS_EXEMPLO
    _FakeItemRepository.sum_total = Decimal("450.93")
    _FakeCusteioRepository.linhas = [
        _linha(
            1,
            custo_mp=Decimal("100"),
            custo_acabamento=Decimal("30"),
            custo_producao=Decimal("50"),
        ),
    ]
    service, session = _make_service(monkeypatch)

    resultado = service.recalcular_preco_item(1)

    # produced cost 100+50+30 = 180; 199 x 1.03 x 1.10 = 225.47; qt 2 -> 450.93.
    assert resultado.custo_produzido == Decimal("180")
    assert resultado.preco_unitario == Decimal("225.47")
    assert resultado.preco_total == Decimal("450.93")
    assert _FakeItemRepository.updated_precos == {
        1: (Decimal("225.47"), Decimal("450.93"))
    }
    assert _FakeItemRepository.updated_versao_total == (7, Decimal("450.93"))
    assert session.committed is True


def test_recalcular_preco_item_sem_custeio_mantem_preco_manual(monkeypatch) -> None:
    """An item without cost lines keeps its manual price; produced cost is 0."""
    _FakeItemRepository.items = [
        _item(1, preco_unitario=Decimal("10"), preco_total=Decimal("10")),
    ]
    _FakeCusteioRepository.linhas = []
    service, _session = _make_service(monkeypatch)

    resultado = service.recalcular_preco_item(1)

    assert resultado.custo_produzido == Decimal("0")
    assert resultado.preco_unitario == Decimal("10")  # manual kept
    assert resultado.preco_total == Decimal("10")
    assert _FakeItemRepository.updated_precos == {}  # nothing written
