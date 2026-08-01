"""Sub-family (subgrupo) of a catalog piece: storage, dialogs and trees."""

from __future__ import annotations

import dataclasses
import inspect

from app.repositories.def_peca_repository import DefPecaRepository
from app.services.def_peca_service import (
    CriarDefPecaData,
    DefPecaService,
    EditarDefPecaData,
)


def test_peca_guarda_e_devolve_a_subfamilia(session) -> None:
    service = DefPecaService(session)

    peca = service.criar_peca(
        CriarDefPecaData(
            codigo="DOBRADICA_TESTE",
            nome="Dobradiça teste",
            grupo="FERRAGENS",
            subgrupo="dobradicas",
        )
    )
    # Normalizada em maiúsculas, como os grupos.
    assert peca.subgrupo == "DOBRADICAS"

    lida = DefPecaRepository(session).get_by_id(peca.id)
    assert lida.subgrupo == "DOBRADICAS"


def test_subfamilia_vazia_fica_a_none(session) -> None:
    peca = DefPecaService(session).criar_peca(
        CriarDefPecaData(codigo="SEM_SUB", nome="Sem sub", grupo="LATERAIS", subgrupo="   ")
    )

    assert peca.subgrupo is None


def test_editar_peca_muda_a_subfamilia(session) -> None:
    service = DefPecaService(session)
    peca = service.criar_peca(
        CriarDefPecaData(
            codigo="PUXADOR_TESTE",
            nome="Puxador teste",
            grupo="FERRAGENS",
            subgrupo="PUXADORES",
        )
    )

    editada = service.editar_peca(
        peca.id,
        EditarDefPecaData(
            codigo=peca.codigo,
            nome=peca.nome,
            grupo="FERRAGENS",
            subgrupo="COZINHAS",
        ),
    )

    assert editada.subgrupo == "COZINHAS"


def test_duplicar_peca_leva_a_subfamilia(session) -> None:
    service = DefPecaService(session)
    peca = service.criar_peca(
        CriarDefPecaData(
            codigo="VARAO_TESTE",
            nome="Varão teste",
            grupo="FERRAGENS",
            subgrupo="ROUPEIROS",
        )
    )

    copia = service.duplicar_peca(peca.id, "VARAO_TESTE_2")

    assert copia.subgrupo == "ROUPEIROS"


def test_revisao_copia_a_subfamilia() -> None:
    from app.services.def_peca_revisao_service import DefPecaRevisaoService

    assert "subgrupo" in DefPecaRevisaoService._CAMPOS_PECA


def test_dialogos_tem_o_campo_subfamilia() -> None:
    from app.ui.dialogs.editar_def_peca_dialog import EditarDefPecaDialogData
    from app.ui.dialogs.nova_def_peca_dialog import NovaDefPecaDialogData

    for data_class in (NovaDefPecaDialogData, EditarDefPecaDialogData):
        campos = {campo.name for campo in dataclasses.fields(data_class)}
        assert "subgrupo" in campos


def test_arvore_das_definicoes_desenha_a_subfamilia() -> None:
    from app.ui.pages.def_pecas_page import DefPecasPage

    fonte = inspect.getsource(DefPecasPage._preencher_arvore)

    assert "peca.subgrupo" in fonte
    assert "_criar_no_arvore" in fonte


def test_biblioteca_do_custeio_desenha_a_subfamilia() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    fonte = inspect.getsource(OrcamentoItemCusteioPage._preencher_biblioteca)

    assert "peca.subgrupo" in fonte
