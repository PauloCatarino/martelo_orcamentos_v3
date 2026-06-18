"""Tests for the temporary-customer service."""

from __future__ import annotations

from datetime import datetime

import pytest

from app.repositories.cliente_repository import ClienteListaResumo
from app.services import cliente_temporario_service as service_module
from app.services.cliente_temporario_service import (
    ClienteEmUsoError,
    ClienteTemporarioService,
    DadosClienteTemporario,
)


def _resumo(cliente_id: int, payload: dict) -> ClienteListaResumo:
    return ClienteListaResumo(
        id=cliente_id,
        nome=payload["nome"],
        nome_simplex=payload["nome_simplex"],
        morada=payload["morada"],
        email=payload["email"],
        pagina_web=payload["pagina_web"],
        telefone=payload["telefone"],
        telemovel=payload["telemovel"],
        num_cliente_phc=payload["num_cliente_phc"],
        info_1=payload["info_1"],
        info_2=payload["info_2"],
        is_temporary=True,
        created_at=datetime(2026, 1, 1),
    )


class _FakeRepository:
    created_payload: dict | None = None
    updated_payload: dict | None = None
    deleted_id: int | None = None
    counted_id: int | None = None
    num_orcamentos = 0

    def __init__(self, _session: object) -> None:
        pass

    def criar(self, **kwargs) -> ClienteListaResumo:
        self.__class__.created_payload = kwargs
        return _resumo(1, kwargs)

    def atualizar(self, *, id: int, **kwargs) -> ClienteListaResumo:
        self.__class__.updated_payload = {"id": id, **kwargs}
        return _resumo(id, kwargs)

    def contar_orcamentos(self, cliente_id: int) -> int:
        self.__class__.counted_id = cliente_id
        return self.num_orcamentos

    def eliminar(self, id: int) -> None:
        self.__class__.deleted_id = id


class _FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    def commit(self) -> None:
        self.commits += 1


def _make_service(monkeypatch) -> tuple[ClienteTemporarioService, _FakeSession]:
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.deleted_id = None
    _FakeRepository.counted_id = None
    _FakeRepository.num_orcamentos = 0
    monkeypatch.setattr(service_module, "ClienteRepository", _FakeRepository)
    session = _FakeSession()
    return ClienteTemporarioService(session), session


def test_criar_gera_simplex_a_partir_do_nome(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    resumo = service.criar(DadosClienteTemporario(nome="  Joao Silva  "))

    assert _FakeRepository.created_payload["nome"] == "Joao Silva"
    assert _FakeRepository.created_payload["nome_simplex"] == "JOAO_SILVA"
    assert resumo.nome_simplex == "JOAO_SILVA"
    assert session.commits == 1


def test_criar_normaliza_simplex_indicado(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    service.criar(DadosClienteTemporario(nome="Joao Silva", nome_simplex=" JS Mob "))

    assert _FakeRepository.created_payload["nome_simplex"] == "JS_MOB"
    assert session.commits == 1


def test_criar_exige_nome_e_nao_faz_commit(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    with pytest.raises(ValueError, match="nome"):
        service.criar(DadosClienteTemporario(nome="   "))

    assert _FakeRepository.created_payload is None
    assert session.commits == 0


def test_editar_exige_nome_e_nao_faz_commit(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    with pytest.raises(ValueError, match="nome"):
        service.editar(5, DadosClienteTemporario(nome="   "))

    assert _FakeRepository.updated_payload is None
    assert session.commits == 0


def test_editar_reenvia_id_e_faz_commit(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    service.editar(
        5,
        DadosClienteTemporario(
            nome=" Cliente Beta ",
            email=" beta@example.test ",
            telefone=" 210000000 ",
        ),
    )

    assert _FakeRepository.updated_payload["id"] == 5
    assert _FakeRepository.updated_payload["nome"] == "Cliente Beta"
    assert _FakeRepository.updated_payload["email"] == "beta@example.test"
    assert _FakeRepository.updated_payload["telefone"] == "210000000"
    assert session.commits == 1


def test_eliminar_bloqueia_cliente_com_orcamentos(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)
    _FakeRepository.num_orcamentos = 2

    with pytest.raises(ClienteEmUsoError) as exc_info:
        service.eliminar(5)

    assert exc_info.value.num_orcamentos == 2
    assert _FakeRepository.counted_id == 5
    assert _FakeRepository.deleted_id is None
    assert session.commits == 0


def test_eliminar_sem_orcamentos_apaga_e_faz_commit(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    service.eliminar(5)

    assert _FakeRepository.counted_id == 5
    assert _FakeRepository.deleted_id == 5
    assert session.commits == 1
