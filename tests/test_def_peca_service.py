"""Tests for the DefPeca service."""

from __future__ import annotations

from app.repositories.def_peca_repository import DefPecaResumo
from app.services import def_peca_service as service_module


class _FakeRepository:
    rows: list[DefPecaResumo] = []
    created_payload: dict[str, object] | None = None
    updated_payload: dict[str, object] | None = None
    deactivate_result = True
    deactivated_id: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self) -> list[DefPecaResumo]:
        return self.rows

    def create_def_peca(self, **kwargs) -> DefPecaResumo:
        self.__class__.created_payload = kwargs
        return DefPecaResumo(
            id=1,
            codigo=kwargs["codigo"],
            nome=kwargs["nome"],
            descricao=kwargs["descricao"],
            grupo=kwargs["grupo"],
            tipo_peca=kwargs["tipo_peca"],
            ativo=kwargs["ativo"],
        )

    def update_def_peca(self, **kwargs) -> DefPecaResumo:
        self.__class__.updated_payload = kwargs
        return DefPecaResumo(
            id=kwargs["id"],
            codigo=kwargs["codigo"],
            nome=kwargs["nome"],
            descricao=kwargs["descricao"],
            grupo=kwargs["grupo"],
            tipo_peca=kwargs["tipo_peca"],
            ativo=kwargs["ativo"],
        )

    def deactivate_def_peca(self, id: int) -> bool:
        self.__class__.deactivated_id = id
        return self.deactivate_result


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def test_def_peca_service_lista_pecas(monkeypatch) -> None:
    _FakeRepository.rows = []
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)

    service = service_module.DefPecaService(session=object())

    assert service.listar_pecas() == []


def test_def_peca_service_cria_peca_com_tipo_default(monkeypatch) -> None:
    _FakeRepository.created_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.criar_peca(
        service_module.CriarDefPecaData(
            codigo=" LAT ",
            nome=" Lateral ",
            descricao="Peca lateral",
            grupo="Roupeiros",
            tipo_peca=None,
        )
    )

    assert _FakeRepository.created_payload is not None
    assert _FakeRepository.created_payload["codigo"] == "LAT"
    assert _FakeRepository.created_payload["nome"] == "Lateral"
    assert _FakeRepository.created_payload["tipo_peca"] == "SIMPLES"
    assert result.tipo_peca == "SIMPLES"
    assert session.committed is True


def test_def_peca_service_normaliza_tipo_ao_editar(monkeypatch) -> None:
    _FakeRepository.updated_payload = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)
    result = service.editar_peca(
        8,
        service_module.EditarDefPecaData(
            codigo="PC",
            nome="Peca Composta",
            descricao=None,
            grupo=None,
            tipo_peca=" composta ",
            ativo=True,
        ),
    )

    assert _FakeRepository.updated_payload is not None
    assert _FakeRepository.updated_payload["id"] == 8
    assert _FakeRepository.updated_payload["tipo_peca"] == "COMPOSTA"
    assert result.tipo_peca == "COMPOSTA"
    assert session.committed is True


def test_def_peca_service_valida_codigo_obrigatorio(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.DefPecaService(session=session)

    try:
        service.criar_peca(service_module.CriarDefPecaData(codigo="", nome="Lateral"))
    except ValueError as error:
        assert "codigo" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_def_peca_service_valida_nome_obrigatorio(monkeypatch) -> None:
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()
    service = service_module.DefPecaService(session=session)

    try:
        service.criar_peca(service_module.CriarDefPecaData(codigo="LAT", nome=""))
    except ValueError as error:
        assert "nome" in str(error)
    else:
        raise AssertionError("Expected ValueError")

    assert session.committed is False


def test_def_peca_service_desativa_peca_existente(monkeypatch) -> None:
    _FakeRepository.deactivate_result = True
    _FakeRepository.deactivated_id = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)

    assert service.desativar_peca(10) is True
    assert _FakeRepository.deactivated_id == 10
    assert session.committed is True


def test_def_peca_service_desativa_peca_inexistente_sem_commit(monkeypatch) -> None:
    _FakeRepository.deactivate_result = False
    _FakeRepository.deactivated_id = None
    monkeypatch.setattr(service_module, "DefPecaRepository", _FakeRepository)
    session = _FakeSession()

    service = service_module.DefPecaService(session=session)

    assert service.desativar_peca(11) is False
    assert _FakeRepository.deactivated_id == 11
    assert session.committed is False
