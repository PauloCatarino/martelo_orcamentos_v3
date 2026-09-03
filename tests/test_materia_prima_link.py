"""O link da ficha da matéria-prima, do formulário até à base e de volta.

Uma referência de catálogo (FER0016) não diz que aspeto tem a ferragem. O campo
é o sítio onde fica a morada na net que mostra o material — a página do
fabricante, a foto do fornecedor. É opcional: não ter link não é aviso nenhum.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.services.def_materia_prima_service import (
    CriarDefMateriaPrimaData,
    DefMateriaPrimaService,
    EditarDefMateriaPrimaData,
)
from app.ui.dialogs.materia_prima_dialog import MateriaPrimaDialog
from app.ui.pages.materias_primas_page import MateriasPrimasPage

_app = QApplication.instance() or QApplication([])

LINK = (
    "https://www.blum.com/pt/pt/products/hinges/clip-top-blumotion/"
    "?articleId=71B3550&view=detail"
)


@pytest.fixture()
def service(session) -> DefMateriaPrimaService:
    return DefMateriaPrimaService(session)


def _criar(service: DefMateriaPrimaService, **overrides):
    campos = {
        "descricao": "DOBRADIÇA BLUM RETA 107º (MOLA) + CALÇO H0",
        "familia_original_excel": "FERRAGENS",
        "tipo_original_excel": "DOBRADICAS",
        "unidade": "UND",
        "preco_tabela": Decimal("1.75"),
        "desconto": Decimal("20"),
    }
    campos.update(overrides)
    return service.criar_materia_prima(CriarDefMateriaPrimaData(**campos))


def test_link_e_gravado_e_lido_de_volta(service) -> None:
    materia = _criar(service, link=LINK)

    assert materia.link == LINK
    assert service.obter_por_id(materia.id).link == LINK


def test_material_sem_link_fica_sem_link(service) -> None:
    materia = _criar(service)

    assert materia.link is None


def test_editar_pode_por_e_tirar_o_link(service) -> None:
    materia = _criar(service)

    com_link = service.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(descricao=materia.descricao, link=LINK),
    )
    assert com_link.link == LINK

    sem_link = service.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(descricao=materia.descricao, link=None),
    )
    assert sem_link.link is None


def test_link_aguenta_uma_morada_comprida(service) -> None:
    # Os catálogos dos fornecedores levam muito parâmetro atrás; um link
    # cortado a meio não abre e não se percebe porquê.
    comprido = "https://catalogo.exemplo.pt/artigo?" + "&".join(
        f"p{n}=valor{n}" for n in range(80)
    )
    assert len(comprido) > 255

    materia = _criar(service, link=comprido)

    assert service.obter_por_id(materia.id).link == comprido


# --- Ficha (diálogo) ---------------------------------------------------------


def test_dialogo_leva_o_link_para_os_dados() -> None:
    dialogo = MateriaPrimaDialog()
    dialogo.descricao_input.setText("DOBRADIÇA BLUM")
    dialogo.link_input.setText(f"  {LINK}  ")

    assert dialogo.get_data().link == LINK
    dialogo.deleteLater()


def test_dialogo_sem_link_devolve_none() -> None:
    dialogo = MateriaPrimaDialog()
    dialogo.descricao_input.setText("DOBRADIÇA BLUM")

    assert dialogo.get_data().link is None
    dialogo.deleteLater()


def test_botao_abrir_so_liga_quando_ha_morada_escrita() -> None:
    dialogo = MateriaPrimaDialog()

    assert not dialogo.abrir_link_button.isEnabled()
    dialogo.link_input.setText(LINK)
    assert dialogo.abrir_link_button.isEnabled()
    dialogo.link_input.setText("   ")
    assert not dialogo.abrir_link_button.isEnabled()
    dialogo.deleteLater()


# --- Tabela ------------------------------------------------------------------


def test_tabela_tem_coluna_link_junto_as_referencias() -> None:
    # A ordem das colunas agrupa o que é da mesma família: primeiro as duas
    # chaves da ponte ao iMos (Ref. PHC e Nome iMos), depois o link e a imagem.
    cabecalhos = MateriasPrimasPage.TABLE_HEADERS

    assert cabecalhos.index("Nome iMos") == cabecalhos.index("Ref. PHC") + 1
    assert cabecalhos.index("Link") == cabecalhos.index("Nome iMos") + 1
    assert cabecalhos.index("Imagem") == cabecalhos.index("Link") + 1
    # O link nasce visível; o nome do ficheiro e o nome do artigo, não.
    assert "Link" not in MateriasPrimasPage.COLUNAS_OCULTAS_POR_DEFEITO
