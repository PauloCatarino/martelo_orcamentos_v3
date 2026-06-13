"""Tests for the quantity-rule service (phase 8T.5.0)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.repositories.def_regra_quantidade_repository import DefRegraQuantidadeResumo
from app.services import def_regra_quantidade_service as service_module
from app.services.def_regra_quantidade_service import (
    CriarRegraQuantidadeData,
    DefRegraQuantidadeService,
    EditarRegraQuantidadeData,
)


def _regra(
    regra_id: int,
    codigo: str,
    *,
    nome: str = "Regra",
    expressao: str = "1",
    descricao: str | None = None,
    ativo: bool = True,
) -> DefRegraQuantidadeResumo:
    return DefRegraQuantidadeResumo(
        id=regra_id,
        codigo=codigo,
        nome=nome,
        expressao=expressao,
        descricao=descricao,
        ativo=ativo,
    )


class _FakeRepository:
    registos: list[DefRegraQuantidadeResumo] = []
    created_payload: dict | None = None
    updated_payload: dict | None = None
    ativo_payload: tuple | None = None

    def __init__(self, _session: object) -> None:
        pass

    def list_all(self) -> list[DefRegraQuantidadeResumo]:
        return list(self.registos)

    def list_ativas(self) -> list[DefRegraQuantidadeResumo]:
        return [r for r in self.registos if r.ativo]

    def get_by_id(self, id: int) -> DefRegraQuantidadeResumo | None:
        return next((r for r in self.registos if r.id == id), None)

    def get_by_codigo(self, codigo: str) -> DefRegraQuantidadeResumo | None:
        return next((r for r in self.registos if r.codigo == codigo), None)

    def create_regra(self, **kwargs) -> DefRegraQuantidadeResumo:
        self.__class__.created_payload = kwargs
        registo = _regra(
            99,
            kwargs["codigo"],
            nome=kwargs["nome"],
            expressao=kwargs["expressao"],
            descricao=kwargs.get("descricao"),
            ativo=kwargs.get("ativo", True),
        )
        self.__class__.registos = [*self.registos, registo]
        return registo

    def update_regra(self, **kwargs) -> DefRegraQuantidadeResumo:
        self.__class__.updated_payload = kwargs
        registo = self.get_by_id(kwargs["id"])
        if registo is None:
            raise ValueError("regra de quantidade nao encontrada")
        return replace(
            registo,
            nome=kwargs["nome"],
            expressao=kwargs["expressao"],
            descricao=kwargs["descricao"],
        )

    def set_ativo(self, id: int, ativo: bool) -> DefRegraQuantidadeResumo:
        self.__class__.ativo_payload = (id, ativo)
        registo = self.get_by_id(id)
        if registo is None:
            raise ValueError("regra de quantidade nao encontrada")
        return replace(registo, ativo=ativo)


class _FakeSession:
    def __init__(self) -> None:
        self.committed = False

    def commit(self) -> None:
        self.committed = True


@pytest.fixture
def service(monkeypatch) -> DefRegraQuantidadeService:
    _FakeRepository.registos = []
    _FakeRepository.created_payload = None
    _FakeRepository.updated_payload = None
    _FakeRepository.ativo_payload = None
    monkeypatch.setattr(service_module, "DefRegraQuantidadeRepository", _FakeRepository)
    return DefRegraQuantidadeService(_FakeSession())


def test_criar_normaliza_codigo_e_valida_expressao(service) -> None:
    resultado = service.criar(
        CriarRegraQuantidadeData(
            codigo=" dobradica ",
            nome="Dobradiças",
            expressao="2 if COMP <= 850 else 3",
            descricao="  ",
        )
    )

    assert resultado.codigo == "DOBRADICA"  # trimmed + uppercased
    assert _FakeRepository.created_payload["codigo"] == "DOBRADICA"
    assert _FakeRepository.created_payload["descricao"] is None  # blank -> None


def test_criar_recusa_expressao_invalida(service) -> None:
    with pytest.raises(ValueError) as erro:
        service.criar(
            CriarRegraQuantidadeData(
                codigo="X", nome="X", expressao="2 +"
            )
        )

    assert "inválida" in str(erro.value).lower()
    assert _FakeRepository.created_payload is None  # nothing created


def test_criar_recusa_variavel_desconhecida(service) -> None:
    with pytest.raises(ValueError) as erro:
        service.criar(
            CriarRegraQuantidadeData(
                codigo="X", nome="X", expressao="ALTURA + 1"
            )
        )

    assert "ALTURA" in str(erro.value)


def test_criar_recusa_codigo_duplicado(service) -> None:
    _FakeRepository.registos = [_regra(1, "DOBRADICA")]

    with pytest.raises(ValueError) as erro:
        service.criar(
            CriarRegraQuantidadeData(codigo="DOBRADICA", nome="X", expressao="1")
        )

    assert "já existe" in str(erro.value).lower()


def test_criar_exige_nome_e_expressao(service) -> None:
    with pytest.raises(ValueError):
        service.criar(CriarRegraQuantidadeData(codigo="X", nome="  ", expressao="1"))
    with pytest.raises(ValueError):
        service.criar(CriarRegraQuantidadeData(codigo="X", nome="X", expressao="  "))


def test_editar_valida_expressao(service) -> None:
    _FakeRepository.registos = [_regra(1, "DOBRADICA")]

    service.editar(
        1,
        EditarRegraQuantidadeData(
            nome="Dobradiças", expressao="CEIL(COMP / 600)", descricao="desc"
        ),
    )

    assert _FakeRepository.updated_payload["expressao"] == "CEIL(COMP / 600)"

    with pytest.raises(ValueError):
        service.editar(1, EditarRegraQuantidadeData(nome="X", expressao="bad +"))


def test_testar_expressao_usa_contexto_exemplo(service) -> None:
    quantidade, motivo = service.testar_expressao("CEIL(COMP / 600)")
    assert motivo is None
    assert quantidade == 4  # COMP=2000 -> ceil(3.33) = 4

    quantidade, motivo = service.testar_expressao(
        "QT_PAI * 2", {"QT_PAI": 3}
    )
    assert motivo is None
    assert quantidade == 6


def test_definir_ativo(service) -> None:
    _FakeRepository.registos = [_regra(1, "PUXADOR", ativo=True)]

    resultado = service.definir_ativo(1, False)

    assert resultado.ativo is False
    assert _FakeRepository.ativo_payload == (1, False)
