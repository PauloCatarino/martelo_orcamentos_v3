"""Tests for the DefValuesetChave service."""

from __future__ import annotations

from app.repositories.def_valueset_chave_repository import DefValuesetChaveResumo
from app.services import def_valueset_chave_service as service_module


def _resumo(**kwargs) -> DefValuesetChaveResumo:
    base = {
        "id": 1,
        "codigo": "MATERIAL_PORTAS",
        "nome": "Material portas",
        "descricao": None,
        "tipo": "MATERIAL",
        "grupo": "MATERIAIS",
        "sistema": False,
        "ativo": True,
        "ordem": 1,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefValuesetChaveResumo(**base)


class _FakeRepository:
    rows: list[DefValuesetChaveResumo] = []
    existing: DefValuesetChaveResumo | None = None
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deactivate_result = True
    activate_result = True

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self):
        return self.rows

    def list_active(self):
        return self.rows

    def list_by_tipo(self, tipo: str):
        return self.rows

    def get_by_id(self, id: int):
        return _resumo(id=id)

    def get_by_codigo(self, codigo: str):
        return self.existing

    def create_chave(self, **fields):
        self.__class__.created_payload = fields
        return _resumo(id=1, **fields)

    def update_chave(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _resumo(id=id, **fields)

    def deactivate_chave(self, id: int) -> bool:
        return self.deactivate_result

    def activate_chave(self, id: int) -> bool:
        return self.activate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.rows = []
    _FakeRepository.existing = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.activate_result = True


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "DefValuesetChaveRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.DefValuesetChaveService(session=session), session


def test_criar_chave_normaliza_codigo_e_defaults(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.criar_chave(
        service_module.CriarDefValuesetChaveData(
            codigo="  material portas ",
            nome="  Material portas ",
            tipo="material",
            grupo="materiais",
        )
    )

    payload = _FakeRepository.created_payload
    assert payload is not None
    assert payload["codigo"] == "MATERIAL_PORTAS"
    assert payload["nome"] == "Material portas"
    assert payload["tipo"] == "MATERIAL"
    assert payload["grupo"] == "MATERIAIS"
    assert payload["sistema"] is False
    assert payload["ativo"] is True
    assert payload["ordem"] == 1
    assert session.committed is True


def test_criar_chave_valida_codigo_obrigatorio(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_chave(
            service_module.CriarDefValuesetChaveData(codigo="  ", nome="Material portas")
        )
    except ValueError as error:
        assert "codigo" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_chave_valida_nome_obrigatorio(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_chave(
            service_module.CriarDefValuesetChaveData(codigo="MATERIAL_PORTAS", nome="  ")
        )
    except ValueError as error:
        assert "nome" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_chave_recusa_codigo_duplicado(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.existing = _resumo(id=9)

    try:
        service.criar_chave(
            service_module.CriarDefValuesetChaveData(
                codigo="MATERIAL_PORTAS", nome="Material portas"
            )
        )
    except ValueError as error:
        assert "codigo" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_listar_opcoes_combo(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.rows = [
        _resumo(id=1, codigo="MATERIAL_PORTAS", nome="Material portas"),
        _resumo(id=2, codigo="FERRAGEM_CORREDICA", nome="Corrediça", tipo="FERRAGEM", grupo="FERRAGENS"),
    ]

    opcoes = service.listar_opcoes_combo()

    assert ("MATERIAL_PORTAS", "Material portas", "MATERIAL", "MATERIAIS") in opcoes
    assert ("FERRAGEM_CORREDICA", "Corrediça", "FERRAGEM", "FERRAGENS") in opcoes


def test_listar_por_tipo_normaliza(monkeypatch) -> None:
    service, _ = _service(monkeypatch)
    _FakeRepository.rows = [_resumo(id=1)]

    assert service.listar_por_tipo("material") == [_resumo(id=1)]
    assert service.listar_por_tipo(None) == []


def test_editar_chave(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    service.editar_chave(
        7,
        service_module.EditarDefValuesetChaveData(
            codigo="ferragem_corredica",
            nome="Corrediça",
            tipo="ferragem",
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 7
    assert _FakeRepository.updated_payload["codigo"] == "FERRAGEM_CORREDICA"
    assert _FakeRepository.updated_payload["tipo"] == "FERRAGEM"
    assert session.committed is True


def test_desativar_existente(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    assert service.desativar_chave(5) is True
    assert session.committed is True


def test_desativar_inexistente_sem_commit(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.deactivate_result = False

    assert service.desativar_chave(5) is False
    assert session.committed is False
