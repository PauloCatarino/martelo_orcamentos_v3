"""Tests for the DefMaquina service."""

from __future__ import annotations

from decimal import Decimal

from app.repositories.def_maquina_repository import DefMaquinaResumo
from app.services import def_maquina_service as service_module


def _resumo(**kwargs) -> DefMaquinaResumo:
    base = {
        "id": 1,
        "codigo": "CORTE",
        "nome": "Corte",
        "descricao": None,
        "tipo": None,
        "custo_hora": None,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefMaquinaResumo(**base)


class _FakeRepository:
    all_rows: list[DefMaquinaResumo] = []
    active_rows: list[DefMaquinaResumo] = []
    by_id: DefMaquinaResumo | None = None
    by_codigo: DefMaquinaResumo | None = None
    requested_codigo: str | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    deactivated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self) -> list[DefMaquinaResumo]:
        return self.all_rows

    def list_active(self) -> list[DefMaquinaResumo]:
        return self.active_rows

    def get_by_id(self, id: int) -> DefMaquinaResumo | None:
        return self.by_id

    def get_by_codigo(self, codigo: str) -> DefMaquinaResumo | None:
        self.__class__.requested_codigo = codigo
        return self.by_codigo

    def create_maquina(self, **kwargs) -> DefMaquinaResumo:
        self.__class__.created_payload = kwargs
        return _resumo(id=1, **kwargs)

    def update_maquina(self, **kwargs) -> DefMaquinaResumo:
        self.__class__.updated_payload = kwargs
        return _resumo(**kwargs)

    def deactivate_maquina(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.all_rows = []
    _FakeRepository.active_rows = []
    _FakeRepository.by_id = None
    _FakeRepository.by_codigo = None
    _FakeRepository.requested_codigo = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "DefMaquinaRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.DefMaquinaService(session=session), session


def test_listar_maquinas(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.all_rows = [_resumo(codigo="CNC")]

    assert service.listar_maquinas() == [_resumo(codigo="CNC")]


def test_obter_por_codigo_normaliza(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(codigo="CORTE")

    result = service.obter_por_codigo(" corte ")

    assert _FakeRepository.requested_codigo == "CORTE"
    assert result.codigo == "CORTE"


def test_criar_maquina_normaliza_codigo_nome_e_commita(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.criar_maquina(
        service_module.CriarDefMaquinaData(
            codigo=" corte ",
            nome=" Corte ",
            tipo="producao",
            custo_hora=Decimal("12.5"),
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["codigo"] == "CORTE"
    assert _FakeRepository.created_payload["nome"] == "Corte"
    assert _FakeRepository.created_payload["tipo"] == "producao"
    assert _FakeRepository.created_payload["custo_hora"] == Decimal("12.5")
    assert result.codigo == "CORTE"
    assert session.committed is True


def test_criar_maquina_recusa_codigo_duplicado(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(id=9, codigo="CORTE")

    try:
        service.criar_maquina(service_module.CriarDefMaquinaData(codigo="CORTE", nome="Corte"))
    except ValueError as error:
        assert "codigo" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_editar_maquina_permite_mesmo_codigo(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(id=5, codigo="CNC")

    result = service.editar_maquina(
        5,
        service_module.EditarDefMaquinaData(codigo=" cnc ", nome="CNC"),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 5
    assert _FakeRepository.updated_payload["codigo"] == "CNC"
    assert result.codigo == "CNC"
    assert session.committed is True


def test_criar_maquina_valida_nome_obrigatorio(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_maquina(service_module.CriarDefMaquinaData(codigo="CNC", nome=" "))
    except ValueError as error:
        assert "nome" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_desativar_maquina_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_maquina(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True


def test_desativar_maquina_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.deactivate_result = False

    assert service.desativar_maquina(11) is False
    assert _FakeRepository.deactivated_id == 11
    assert session.committed is False
