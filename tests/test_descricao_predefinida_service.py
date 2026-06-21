"""Tests for the predefined-descriptions service (phase P6a)."""

from __future__ import annotations

import pytest

from app.repositories.descricao_predefinida_repository import DescricaoPredefinidaResumo
from app.services import descricao_predefinida_service as service_module
from app.services.descricao_predefinida_service import DescricaoPredefinidaService


def _resumo(id: int = 1, texto: str = "texto", tipo: str = "-", ordem: int = 1) -> DescricaoPredefinidaResumo:
    return DescricaoPredefinidaResumo(id=id, texto=texto, tipo=tipo, ordem=ordem)


class _FakeRepository:
    listar_args: tuple | None = None
    criar_args: tuple | None = None
    atualizar_args: tuple | None = None
    eliminar_args: tuple | None = None
    mover_args: tuple | None = None
    mover_resultado: bool = True

    def __init__(self, _session: object) -> None:
        pass

    def list_by_user(self, user_id, termos=None):
        self.__class__.listar_args = (user_id, list(termos) if termos is not None else None)
        return [_resumo()]

    def criar(self, user_id, texto, tipo):
        self.__class__.criar_args = (user_id, texto, tipo)
        return _resumo(texto=texto, tipo=tipo)

    def atualizar(self, id, user_id, texto, tipo):
        self.__class__.atualizar_args = (id, user_id, texto, tipo)
        return _resumo(id=id, texto=texto, tipo=tipo)

    def eliminar(self, user_id, ids):
        self.__class__.eliminar_args = (user_id, list(ids))
        return len(list(ids))

    def mover(self, id, user_id, direcao):
        self.__class__.mover_args = (id, user_id, direcao)
        return self.__class__.mover_resultado


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _make_service(monkeypatch) -> tuple[DescricaoPredefinidaService, _FakeSession]:
    _FakeRepository.listar_args = None
    _FakeRepository.criar_args = None
    _FakeRepository.atualizar_args = None
    _FakeRepository.eliminar_args = None
    _FakeRepository.mover_args = None
    _FakeRepository.mover_resultado = True
    monkeypatch.setattr(
        service_module, "DescricaoPredefinidaRepository", _FakeRepository
    )
    session = _FakeSession()
    return DescricaoPredefinidaService(session), session


def test_criar_texto_vazio_levanta_e_nao_commita(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    with pytest.raises(ValueError):
        service.criar(7, "   ", "-")

    assert _FakeRepository.criar_args is None
    assert session.committed is False


def test_criar_sem_user_levanta(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    with pytest.raises(ValueError):
        service.criar(0, "texto", "-")

    assert _FakeRepository.criar_args is None
    assert session.committed is False


def test_criar_delega_no_repo_e_commita(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    service.criar(7, "  Gaveta com LED  ", "*")

    # Texto chega ao repo já sem espaços nas pontas.
    assert _FakeRepository.criar_args == (7, "Gaveta com LED", "*")
    assert session.committed is True


def test_editar_delega_no_repo_e_commita(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    service.editar(3, 7, "  Novo texto ", "-")

    assert _FakeRepository.atualizar_args == (3, 7, "Novo texto", "-")
    assert session.committed is True


def test_editar_texto_vazio_levanta_e_nao_commita(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    with pytest.raises(ValueError):
        service.editar(3, 7, "", "-")

    assert _FakeRepository.atualizar_args is None
    assert session.committed is False


def test_eliminar_delega_no_repo_e_commita(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)

    total = service.eliminar(7, [1, 2, 3])

    assert total == 3
    assert _FakeRepository.eliminar_args == (7, [1, 2, 3])
    assert session.committed is True


def test_mover_commita_quando_repo_devolve_true(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)
    _FakeRepository.mover_resultado = True

    assert service.mover(1, 7, "up") is True
    assert _FakeRepository.mover_args == (1, 7, "up")
    assert session.committed is True


def test_mover_nao_commita_quando_repo_devolve_false(monkeypatch) -> None:
    service, session = _make_service(monkeypatch)
    _FakeRepository.mover_resultado = False

    assert service.mover(1, 7, "down") is False
    assert _FakeRepository.mover_args == (1, 7, "down")
    assert session.committed is False


def test_listar_divide_texto_por_percentagem(monkeypatch) -> None:
    service, _session = _make_service(monkeypatch)

    service.listar(7, "gaveta%led")

    assert _FakeRepository.listar_args == (7, ["gaveta", "led"])


def test_listar_sem_texto_passa_none(monkeypatch) -> None:
    service, _session = _make_service(monkeypatch)

    service.listar(7)

    assert _FakeRepository.listar_args == (7, None)
