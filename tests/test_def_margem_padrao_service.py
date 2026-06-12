"""Tests for the default-margin service (phase 8T.1)."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

import pytest

from app.domain.precos import MargensOrcamento
from app.repositories.def_margem_padrao_repository import DefMargemPadraoResumo
from app.services import def_margem_padrao_service as service_module
from app.services.def_margem_padrao_service import (
    CriarMargemPadraoData,
    DefMargemPadraoService,
    EditarMargemPadraoData,
    ORIGEM_CLIENTE,
    ORIGEM_STANDARD,
    ORIGEM_UTILIZADOR,
    ORIGEM_ZEROS,
)


def _registo(
    registo_id: int,
    ambito: str,
    *,
    cliente_id: int | None = None,
    user_id: int | None = None,
    lucro: Decimal = Decimal("0"),
    ativo: bool = True,
) -> DefMargemPadraoResumo:
    return DefMargemPadraoResumo(
        id=registo_id,
        ambito=ambito,
        cliente_id=cliente_id,
        user_id=user_id,
        margem_lucro_pct=lucro,
        margem_mp_pct=Decimal("0"),
        margem_mao_obra_pct=Decimal("0"),
        margem_acabamentos_pct=Decimal("0"),
        custos_administrativos_pct=Decimal("0"),
        ativo=ativo,
    )


class _FakeRepository:
    registos: list[DefMargemPadraoResumo] = []
    created_payload: dict | None = None
    updated_payload: dict | None = None
    ativo_payload: tuple | None = None
    cliente_id_por_contacto: int | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_by_ambito(self, ambito: str) -> list[DefMargemPadraoResumo]:
        return [r for r in self.registos if r.ambito == ambito]

    def get_by_id(self, id: int) -> DefMargemPadraoResumo | None:
        return next((r for r in self.registos if r.id == id), None)

    def get_standard(self) -> DefMargemPadraoResumo | None:
        return next((r for r in self.registos if r.ambito == "STANDARD"), None)

    def get_by_cliente(self, cliente_id: int) -> DefMargemPadraoResumo | None:
        return next(
            (r for r in self.registos if r.cliente_id == cliente_id), None
        )

    def get_by_user(self, user_id: int) -> DefMargemPadraoResumo | None:
        return next((r for r in self.registos if r.user_id == user_id), None)

    def get_margens_ativas_standard(self) -> MargensOrcamento | None:
        registo = self.get_standard()
        if registo is None or not registo.ativo:
            return None
        return registo.to_margens()

    def get_margens_ativas_por_cliente(self, cliente_id: int) -> MargensOrcamento | None:
        registo = self.get_by_cliente(cliente_id)
        if registo is None or not registo.ativo:
            return None
        return registo.to_margens()

    def get_margens_ativas_por_user(self, user_id: int) -> MargensOrcamento | None:
        registo = self.get_by_user(user_id)
        if registo is None or not registo.ativo:
            return None
        return registo.to_margens()

    def find_cliente_id_por_contacto(self, nome, email) -> int | None:
        return self.cliente_id_por_contacto

    def create_margem(self, **kwargs) -> DefMargemPadraoResumo:
        self.__class__.created_payload = kwargs
        registo = _registo(
            99,
            kwargs["ambito"],
            cliente_id=kwargs.get("cliente_id"),
            user_id=kwargs.get("user_id"),
            lucro=kwargs.get("margem_lucro_pct", Decimal("0")),
        )
        self.__class__.registos = [*self.registos, registo]
        return registo

    def update_margens(self, **kwargs) -> DefMargemPadraoResumo:
        self.__class__.updated_payload = kwargs
        registo = self.get_by_id(kwargs["id"])
        if registo is None:
            raise ValueError("registo de margens nao encontrado")
        return replace(registo, margem_lucro_pct=kwargs["margem_lucro_pct"])

    def set_ativo(self, id: int, ativo: bool) -> DefMargemPadraoResumo:
        self.__class__.ativo_payload = (id, ativo)
        registo = self.get_by_id(id)
        if registo is None:
            raise ValueError("registo de margens nao encontrado")
        return replace(registo, ativo=ativo)


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


def _make_service(monkeypatch) -> tuple[DefMargemPadraoService, _FakeSession]:
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.ativo_payload = None
    _FakeRepository.cliente_id_por_contacto = None
    monkeypatch.setattr(
        service_module, "DefMargemPadraoRepository", _FakeRepository
    )
    session = _FakeSession()
    return DefMargemPadraoService(session), session


def test_criar_registo_cliente(monkeypatch) -> None:
    _FakeRepository.registos = []
    service, session = _make_service(monkeypatch)

    service.criar(
        CriarMargemPadraoData(
            ambito="CLIENTE", cliente_id=4, margem_lucro_pct=Decimal("12")
        )
    )

    assert _FakeRepository.created_payload["ambito"] == "CLIENTE"
    assert _FakeRepository.created_payload["cliente_id"] == 4
    assert _FakeRepository.created_payload["user_id"] is None
    assert session.committed is True


def test_criar_exige_cliente_e_user_conforme_ambito(monkeypatch) -> None:
    _FakeRepository.registos = []
    service, _session = _make_service(monkeypatch)

    with pytest.raises(ValueError, match="cliente_id"):
        service.criar(CriarMargemPadraoData(ambito="CLIENTE"))

    with pytest.raises(ValueError, match="user_id"):
        service.criar(CriarMargemPadraoData(ambito="UTILIZADOR"))

    with pytest.raises(ValueError, match="ambito"):
        service.criar(CriarMargemPadraoData(ambito="OUTRO"))


def test_criar_respeita_unicidade_por_ambito(monkeypatch) -> None:
    _FakeRepository.registos = [
        _registo(1, "STANDARD"),
        _registo(2, "CLIENTE", cliente_id=4),
        _registo(3, "UTILIZADOR", user_id=7),
    ]
    service, _session = _make_service(monkeypatch)

    with pytest.raises(ValueError, match="STANDARD"):
        service.criar(CriarMargemPadraoData(ambito="STANDARD"))

    with pytest.raises(ValueError, match="cliente"):
        service.criar(CriarMargemPadraoData(ambito="CLIENTE", cliente_id=4))

    with pytest.raises(ValueError, match="utilizador"):
        service.criar(CriarMargemPadraoData(ambito="UTILIZADOR", user_id=7))

    # Another customer/user is still allowed.
    service.criar(CriarMargemPadraoData(ambito="CLIENTE", cliente_id=5))
    assert _FakeRepository.created_payload["cliente_id"] == 5


def test_guardar_standard_cria_e_depois_atualiza(monkeypatch) -> None:
    _FakeRepository.registos = []
    service, session = _make_service(monkeypatch)

    service.guardar_standard(EditarMargemPadraoData(margem_lucro_pct=Decimal("10")))
    assert _FakeRepository.created_payload["ambito"] == "STANDARD"
    assert session.committed is True

    service.guardar_standard(EditarMargemPadraoData(margem_lucro_pct=Decimal("12")))
    assert _FakeRepository.updated_payload["id"] == 99
    assert _FakeRepository.updated_payload["margem_lucro_pct"] == Decimal("12")


def test_editar_registo(monkeypatch) -> None:
    _FakeRepository.registos = [_registo(2, "CLIENTE", cliente_id=4)]
    service, session = _make_service(monkeypatch)

    service.editar(2, EditarMargemPadraoData(margem_lucro_pct=Decimal("8")))

    assert _FakeRepository.updated_payload["id"] == 2
    assert session.committed is True


def test_resolver_margens_padrao_ordem_cliente_utilizador_standard(monkeypatch) -> None:
    _FakeRepository.registos = [
        _registo(1, "STANDARD", lucro=Decimal("10")),
        _registo(2, "CLIENTE", cliente_id=4, lucro=Decimal("20")),
        _registo(3, "UTILIZADOR", user_id=7, lucro=Decimal("30")),
    ]
    service, _session = _make_service(monkeypatch)

    margens, origem = service.resolver_margens_padrao(4, 7)
    assert origem == ORIGEM_CLIENTE
    assert margens.margem_lucro_pct == Decimal("20")

    # No customer record -> the user's wins.
    margens, origem = service.resolver_margens_padrao(99, 7)
    assert origem == ORIGEM_UTILIZADOR
    assert margens.margem_lucro_pct == Decimal("30")

    # Neither customer nor user -> STANDARD.
    margens, origem = service.resolver_margens_padrao(99, 99)
    assert origem == ORIGEM_STANDARD
    assert margens.margem_lucro_pct == Decimal("10")


def test_resolver_margens_padrao_ignora_inativos_e_cai_para_zeros(monkeypatch) -> None:
    _FakeRepository.registos = [
        _registo(1, "STANDARD", lucro=Decimal("10"), ativo=False),
        _registo(2, "CLIENTE", cliente_id=4, lucro=Decimal("20"), ativo=False),
    ]
    service, _session = _make_service(monkeypatch)

    margens, origem = service.resolver_margens_padrao(4, None)

    assert origem == ORIGEM_ZEROS
    assert margens == MargensOrcamento()


def test_margens_cliente_por_contacto(monkeypatch) -> None:
    _FakeRepository.registos = [
        _registo(2, "CLIENTE", cliente_id=4, lucro=Decimal("20")),
    ]
    service, _session = _make_service(monkeypatch)

    _FakeRepository.cliente_id_por_contacto = None
    assert service.margens_cliente_por_contacto("Cliente X", None) is None

    _FakeRepository.cliente_id_por_contacto = 4
    margens = service.margens_cliente_por_contacto("Cliente X", None)
    assert margens is not None
    assert margens.margem_lucro_pct == Decimal("20")


def test_definir_ativo(monkeypatch) -> None:
    _FakeRepository.registos = [_registo(2, "CLIENTE", cliente_id=4)]
    service, session = _make_service(monkeypatch)

    service.definir_ativo(2, False)

    assert _FakeRepository.ativo_payload == (2, False)
    assert session.committed is True
