"""Tests for the DefValuesetModelo service."""

from __future__ import annotations

from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services import def_valueset_modelo_service as service_module


def _resumo(**kwargs) -> DefValuesetModeloResumo:
    base = {
        "id": 1,
        "codigo": "BASE",
        "nome": "Base",
        "descricao": None,
        "tipo": None,
        "ambito": "UTILIZADOR",
        "user_id": None,
        "visivel_para_todos": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefValuesetModeloResumo(**base)


class _FakeRepository:
    rows: list[DefValuesetModeloResumo] = []
    active_rows: list[DefValuesetModeloResumo] = []
    by_codigo: DefValuesetModeloResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    activate_result = True
    deactivated_id: int | None = None
    activated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self):
        return self.rows

    def list_active(self):
        return self.active_rows

    def get_by_id(self, id: int):
        return _resumo(id=id)

    def get_by_codigo(self, codigo: str):
        return self.by_codigo

    def create(self, **fields):
        self.__class__.created_payload = fields
        return _resumo(id=1, **fields)

    def update(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _resumo(id=id, **fields)

    def deactivate(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result

    def activate(self, id: int) -> bool:
        self.__class__.activated_id = id
        return self.activate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.rows = []
    _FakeRepository.active_rows = []
    _FakeRepository.by_codigo = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.activate_result = True
    _FakeRepository.deactivated_id = None
    _FakeRepository.activated_id = None


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "DefValuesetModeloRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.DefValuesetModeloService(session=session), session


def test_listar_modelos(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.rows = [_resumo(id=3)]

    assert service.listar_modelos() == [_resumo(id=3)]


def test_listar_modelos_utilizador_e_globais(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.active_rows = [
        _resumo(id=1, codigo="USER", ambito="UTILIZADOR", visivel_para_todos=False),
        _resumo(id=2, codigo="GLOB", ambito="GLOBAL", visivel_para_todos=False),
        _resumo(id=3, codigo="SHARED", ambito="UTILIZADOR", visivel_para_todos=True),
    ]

    utilizador = service.listar_modelos_utilizador()
    globais = service.listar_modelos_globais()

    assert [modelo.codigo for modelo in utilizador] == ["USER"]
    assert sorted(modelo.codigo for modelo in globais) == ["GLOB", "SHARED"]


def test_criar_modelo_normaliza_campos(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.criar_modelo(
        service_module.CriarDefValuesetModeloData(
            codigo=" BASE ",
            nome=" Modelo Base ",
            tipo=" roupeiro ",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["codigo"] == "BASE"
    assert _FakeRepository.created_payload["nome"] == "Modelo Base"
    assert _FakeRepository.created_payload["tipo"] == "roupeiro"
    assert result.codigo == "BASE"
    assert session.committed is True


def test_criar_modelo_inclui_ambito_e_codigo_upper(monkeypatch) -> None:
    service, _ = _service(monkeypatch)

    service.criar_modelo(
        service_module.CriarDefValuesetModeloData(
            codigo="roupeiro standard",
            nome="Roupeiro standard",
            ambito="global",
            visivel_para_todos=True,
        )
    )

    payload = _FakeRepository.created_payload
    assert payload["codigo"] == "ROUPEIRO_STANDARD"
    assert payload["ambito"] == "GLOBAL"
    assert payload["visivel_para_todos"] is True


def test_criar_modelo_recusa_codigo_duplicado(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(id=9, codigo="BASE")

    try:
        service.criar_modelo(
            service_module.CriarDefValuesetModeloData(codigo="BASE", nome="Base")
        )
    except ValueError as error:
        assert "codigo" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_editar_modelo_permite_mesmo_codigo_da_propria_linha(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.by_codigo = _resumo(id=5, codigo="BASE")

    result = service.editar_modelo(
        5,
        service_module.EditarDefValuesetModeloData(codigo="BASE", nome="Base Editada"),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 5
    assert result.nome == "Base Editada"
    assert session.committed is True


def test_desativar_e_ativar_modelo(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_modelo(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True

    session.committed = False
    assert service.ativar_modelo(10) is True
    assert _FakeRepository.activated_id == 10
    assert session.committed is True
