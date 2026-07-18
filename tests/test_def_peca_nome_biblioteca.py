"""Tests for the piece library display name (nome_biblioteca)."""

from __future__ import annotations

from app.services.def_peca_revisao_service import DefPecaRevisaoService
from app.services.def_peca_service import (
    CriarDefPecaData,
    DefPecaService,
    EditarDefPecaData,
)


def _criar_peca(service: DefPecaService, **overrides):
    data = CriarDefPecaData(
        codigo=overrides.pop("codigo", "COSTA_ONS_0000"),
        nome=overrides.pop("nome", "COSTA_ONS"),
        grupo="COSTAS",
        natureza="MATERIAL",
        **overrides,
    )
    return service.criar_peca(data)


def test_criar_peca_guarda_nome_biblioteca(session) -> None:
    service = DefPecaService(session)

    peca = _criar_peca(service, nome_biblioteca="  Costa ONS  ")

    assert peca.nome_biblioteca == "Costa ONS"


def test_criar_peca_sem_nome_biblioteca_fica_none(session) -> None:
    service = DefPecaService(session)

    peca = _criar_peca(service, nome_biblioteca="   ")

    assert peca.nome_biblioteca is None


def test_editar_peca_atualiza_e_limpa_nome_biblioteca(session) -> None:
    service = DefPecaService(session)
    peca = _criar_peca(service, nome_biblioteca="Costa ONS")

    editada = service.editar_peca(
        peca.id,
        EditarDefPecaData(
            codigo=peca.codigo,
            nome=peca.nome,
            grupo=peca.grupo,
            natureza=peca.natureza,
            nome_biblioteca="Costa nova",
        ),
    )
    assert editada.nome_biblioteca == "Costa nova"

    limpa = service.editar_peca(
        peca.id,
        EditarDefPecaData(
            codigo=peca.codigo,
            nome=peca.nome,
            grupo=peca.grupo,
            natureza=peca.natureza,
            nome_biblioteca=None,
        ),
    )
    assert limpa.nome_biblioteca is None


def test_duplicar_peca_copia_nome_biblioteca(session) -> None:
    service = DefPecaService(session)
    peca = _criar_peca(service, nome_biblioteca="Costa ONS")

    copia = service.duplicar_peca(peca.id, "COSTA_ONS_COPIA")

    assert copia.nome_biblioteca == "Costa ONS"


def test_criar_revisao_copia_nome_biblioteca(session) -> None:
    service = DefPecaService(session)
    peca = _criar_peca(service, nome_biblioteca="Costa ONS")

    resultado = DefPecaRevisaoService(session).criar_revisao(peca.id)

    nova = DefPecaService(session).repository.get_by_id(resultado.nova_peca_id)
    assert nova is not None
    assert nova.nome_biblioteca == "Costa ONS"
