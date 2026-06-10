"""Tests for the machine area-tier service (phase 8S.0)."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.def_maquina_escalao_area_repository import (
    DefMaquinaEscalaoAreaResumo,
)
from app.services import def_maquina_escalao_area_service as service_module


def _resumo(**kwargs) -> DefMaquinaEscalaoAreaResumo:
    base = {
        "id": 1,
        "def_maquina_id": 7,
        "nivel": 1,
        "area_max_m2": None,
        "preco_peca_std": None,
        "preco_peca_serie": None,
        "ativo": True,
    }
    base.update(kwargs)
    return DefMaquinaEscalaoAreaResumo(**base)


class _FakeRepository:
    by_maquina: list = []
    active_by_maquina: list = []
    by_id: DefMaquinaEscalaoAreaResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivated_id: int | None = None
    activated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_by_maquina(self, def_maquina_id: int):
        return self.by_maquina

    def list_active_by_maquina(self, def_maquina_id: int):
        return self.active_by_maquina

    def get_by_id(self, id: int):
        return self.by_id

    def create_escalao(self, **kwargs):
        self.__class__.created_payload = kwargs
        return _resumo(id=1, **kwargs)

    def update_escalao(self, **kwargs):
        self.__class__.updated_payload = kwargs
        return _resumo(**kwargs)

    def deactivate_escalao(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return True

    def activate_escalao(self, id: int) -> bool:
        self.__class__.activated_id = id
        return True


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _service(monkeypatch):
    _FakeRepository.by_maquina = []
    _FakeRepository.active_by_maquina = []
    _FakeRepository.by_id = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivated_id = None
    _FakeRepository.activated_id = None
    monkeypatch.setattr(
        service_module, "DefMaquinaEscalaoAreaRepository", _FakeRepository
    )
    session = _FakeSession()
    return service_module.DefMaquinaEscalaoAreaService(session=session), session


def test_listar_por_maquina(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_maquina = [_resumo(id=1, nivel=1), _resumo(id=2, nivel=2)]

    result = service.listar_escaloes_da_maquina(7)

    assert [e.nivel for e in result] == [1, 2]


def test_adicionar_escalao(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.adicionar_escalao(
        service_module.CriarEscalaoAreaData(
            def_maquina_id=7,
            nivel=1,
            area_max_m2=Decimal("0.25"),
            preco_peca_std=Decimal("1.20"),
            preco_peca_serie=Decimal("0.90"),
        )
    )

    payload = _FakeRepository.created_payload
    assert payload["def_maquina_id"] == 7
    assert payload["area_max_m2"] == Decimal("0.25")
    assert payload["preco_peca_std"] == Decimal("1.20")
    assert result.def_maquina_id == 7
    assert session.committed is True


def test_adicionar_normaliza_nivel(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.adicionar_escalao(
        service_module.CriarEscalaoAreaData(def_maquina_id=7, nivel=0)
    )

    assert _FakeRepository.created_payload["nivel"] == 1


def test_adicionar_valida_maquina_id(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.adicionar_escalao(
            service_module.CriarEscalaoAreaData(def_maquina_id=None)
        )
    except ValueError:
        pass
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_editar_escalao(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.editar_escalao(
        5,
        service_module.EditarEscalaoAreaData(
            nivel=5,
            area_max_m2=None,
            preco_peca_std=Decimal("5.50"),
            preco_peca_serie=Decimal("4.10"),
        ),
    )

    payload = _FakeRepository.updated_payload
    assert payload["id"] == 5
    assert payload["area_max_m2"] is None  # last tier -> no limit
    assert payload["preco_peca_std"] == Decimal("5.50")


def test_desativar_e_ativar(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_escalao(9) is True
    assert _FakeRepository.deactivated_id == 9
    assert service.ativar_escalao(9) is True
    assert _FakeRepository.activated_id == 9
    assert session.committed is True
