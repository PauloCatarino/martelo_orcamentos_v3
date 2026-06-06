"""Tests for the DefValuesetModeloLinha service."""

from __future__ import annotations

from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaResumo
from app.services import def_valueset_modelo_linha_service as service_module


def _resumo(**kwargs) -> DefValuesetModeloLinhaResumo:
    base = {
        "id": 1,
        "def_valueset_modelo_id": 10,
        "chave": "MATERIAL_CAIXOTE",
        "descricao": None,
        "materia_prima_id": None,
        "ref_materia_prima": None,
        "descricao_materia_prima": None,
        "valor_texto": None,
        "origem": None,
        "editado_localmente": False,
        "ativo": True,
        "observacoes": None,
    }
    base.update(kwargs)
    return DefValuesetModeloLinhaResumo(**base)


class _FakeRepository:
    rows: list[DefValuesetModeloLinhaResumo] = []
    duplicate: DefValuesetModeloLinhaResumo | None = None
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

    def list_by_modelo(self, modelo_id: int):
        return self.rows

    def get_by_id(self, id: int):
        return _resumo(id=id)

    def get_by_modelo_chave(self, modelo_id: int, chave: str):
        return self.duplicate

    def create(self, **fields):
        self.__class__.created_payload = fields
        return _resumo(id=1, **fields)

    def update(self, *, id: int, **fields):
        self.__class__.updated_payload = {"id": id, **fields}
        return _resumo(id=id, **fields)

    def deactivate(self, id: int) -> bool:
        return self.deactivate_result

    def activate(self, id: int) -> bool:
        return self.activate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _reset() -> None:
    _FakeRepository.rows = []
    _FakeRepository.duplicate = None
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deactivate_result = True
    _FakeRepository.activate_result = True


def _service(monkeypatch):
    _reset()
    monkeypatch.setattr(service_module, "DefValuesetModeloLinhaRepository", _FakeRepository)
    session = _FakeSession()
    return service_module.DefValuesetModeloLinhaService(session=session), session


def test_criar_linha_normaliza_chave_e_defaults(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    result = service.criar_linha(
        service_module.CriarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave=" material_caixote ",
            ref_materia_prima="PLACA-01",
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["chave"] == "MATERIAL_CAIXOTE"
    assert _FakeRepository.created_payload["editado_localmente"] is False
    assert _FakeRepository.created_payload["ativo"] is True
    assert result.ref_materia_prima == "PLACA-01"
    assert session.committed is True


def test_criar_linha_valida_chave_obrigatoria(monkeypatch) -> None:
    service, session = _service(monkeypatch)

    try:
        service.criar_linha(
            service_module.CriarDefValuesetModeloLinhaData(
                def_valueset_modelo_id=10,
                chave=" ",
            )
        )
    except ValueError as error:
        assert "chave" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_criar_linha_recusa_chave_duplicada(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.duplicate = _resumo(id=2)

    try:
        service.criar_linha(
            service_module.CriarDefValuesetModeloLinhaData(
                def_valueset_modelo_id=10,
                chave="MATERIAL_CAIXOTE",
            )
        )
    except ValueError as error:
        assert "chave" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_editar_linha_permite_a_propria_chave(monkeypatch) -> None:
    service, session = _service(monkeypatch)
    _FakeRepository.duplicate = _resumo(id=7)

    result = service.editar_linha(
        7,
        service_module.EditarDefValuesetModeloLinhaData(
            def_valueset_modelo_id=10,
            chave="ORLA_FINA",
            valor_texto="orla fina default",
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 7
    assert _FakeRepository.updated_payload["chave"] == "ORLA_FINA"
    assert result.valor_texto == "orla fina default"
    assert session.committed is True
