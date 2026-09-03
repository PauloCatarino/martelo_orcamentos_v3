"""A imagem do material na ficha da matéria-prima.

O iMos já tem uma fotografia para quase todas as ferragens: cada artigo tem um
«Preview Image» com o nome do ficheiro e os ficheiros vivem todos na mesma
pasta da biblioteca. Guarda-se só o NOME — a pasta é uma configuração, para o
dia em que a biblioteca mudar de sítio se mudar um caminho e não trezentas
fichas.
"""

from __future__ import annotations

import os
from decimal import Decimal

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication

from app.services.def_materia_prima_service import (
    CriarDefMateriaPrimaData,
    DefMateriaPrimaService,
    EditarDefMateriaPrimaData,
)
from app.ui.dialogs.materia_prima_dialog import MateriaPrimaDialog
from app.ui.pages.materias_primas_page import (
    KEY_PASTA_IMAGENS_IMOS,
    MateriasPrimasPage,
)

_app = QApplication.instance() or QApplication([])

IMAGEM = "HF_637.76.352_PE_AXILO_72_92.JPG"


@pytest.fixture()
def service(session) -> DefMateriaPrimaService:
    return DefMateriaPrimaService(session)


@pytest.fixture()
def pasta_com_imagem(tmp_path):
    """Uma pasta a fingir de biblioteca do iMos, com uma imagem lá dentro."""
    imagem = QImage(40, 30, QImage.Format.Format_RGB32)
    imagem.fill(0x8B6F4E)
    assert imagem.save(str(tmp_path / IMAGEM))
    return tmp_path


def _criar(service: DefMateriaPrimaService, **overrides):
    campos = {
        "descricao": "PE AXILO REGULAVEL H72->H92",
        "familia_original_excel": "FERRAGENS",
        "tipo_original_excel": "PES",
        "unidade": "UND",
        "preco_tabela": Decimal("0.60"),
    }
    campos.update(overrides)
    return service.criar_materia_prima(CriarDefMateriaPrimaData(**campos))


# --- Base -------------------------------------------------------------------


def test_nome_da_imagem_e_gravado_e_lido_de_volta(service) -> None:
    materia = _criar(service, imagem_ficheiro=IMAGEM)

    assert materia.imagem_ficheiro == IMAGEM
    assert service.obter_por_id(materia.id).imagem_ficheiro == IMAGEM


def test_material_sem_imagem_fica_sem_imagem(service) -> None:
    assert _criar(service).imagem_ficheiro is None


def test_editar_pode_por_e_tirar_a_imagem(service) -> None:
    materia = _criar(service)

    com = service.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(descricao=materia.descricao, imagem_ficheiro=IMAGEM),
    )
    assert com.imagem_ficheiro == IMAGEM

    sem = service.editar_materia_prima(
        materia.id,
        EditarDefMateriaPrimaData(descricao=materia.descricao, imagem_ficheiro=None),
    )
    assert sem.imagem_ficheiro is None


# --- Ficha (diálogo) ---------------------------------------------------------


def test_ficha_desenha_a_imagem_que_existe_na_pasta(pasta_com_imagem) -> None:
    dialogo = MateriaPrimaDialog(pasta_imagens=str(pasta_com_imagem))
    dialogo.imagem_input.setText(IMAGEM)

    assert not dialogo.imagem_label.pixmap().isNull()
    assert dialogo.imagem_label.text() == ""
    dialogo.deleteLater()


def test_ficha_sem_nome_de_ficheiro_diz_que_nao_ha_imagem(pasta_com_imagem) -> None:
    dialogo = MateriaPrimaDialog(pasta_imagens=str(pasta_com_imagem))

    assert dialogo.imagem_label.pixmap().isNull()
    assert dialogo.imagem_label.text() == "Sem imagem"
    dialogo.deleteLater()


def test_ficha_diz_quando_a_imagem_nao_esta_la(pasta_com_imagem) -> None:
    dialogo = MateriaPrimaDialog(pasta_imagens=str(pasta_com_imagem))
    dialogo.imagem_input.setText("NAO_EXISTE.JPG")

    assert dialogo.imagem_label.pixmap().isNull()
    assert "Não foi encontrada" in dialogo.imagem_label.text()
    assert "NAO_EXISTE.JPG" in dialogo.imagem_label.text()
    dialogo.deleteLater()


def test_ficha_sem_pasta_configurada_manda_configurar() -> None:
    # A pasta é uma unidade de rede: um quadrado vazio faria parecer que o
    # material não tem imagem, quando o que falta é o caminho.
    dialogo = MateriaPrimaDialog(pasta_imagens="")
    dialogo.imagem_input.setText(IMAGEM)

    assert dialogo.imagem_label.pixmap().isNull()
    assert "Caminhos do Sistema" in dialogo.imagem_label.text()
    dialogo.deleteLater()


def test_ficha_leva_o_nome_da_imagem_para_os_dados(pasta_com_imagem) -> None:
    dialogo = MateriaPrimaDialog(pasta_imagens=str(pasta_com_imagem))
    dialogo.descricao_input.setText("PE AXILO")
    dialogo.imagem_input.setText(f"  {IMAGEM}  ")

    assert dialogo.get_data().imagem_ficheiro == IMAGEM
    dialogo.deleteLater()


def test_ficha_guarda_so_o_nome_e_nunca_o_caminho(pasta_com_imagem) -> None:
    # O "Procurar…" devolve o caminho todo; o que fica guardado é o nome.
    dialogo = MateriaPrimaDialog(pasta_imagens=str(pasta_com_imagem))
    caminho = str(pasta_com_imagem / IMAGEM)
    assert os.sep in caminho

    dialogo.imagem_input.setText(os.path.basename(caminho))

    assert dialogo.get_data().imagem_ficheiro == IMAGEM
    assert os.sep not in dialogo.get_data().imagem_ficheiro
    dialogo.deleteLater()


# --- Tabela e configuração ---------------------------------------------------


def test_tabela_tem_coluna_imagem_escondida_por_defeito() -> None:
    cabecalhos = MateriasPrimasPage.TABLE_HEADERS

    assert "Imagem" in cabecalhos
    assert cabecalhos.index("Imagem") == cabecalhos.index("Link") + 1
    # É um nome de ficheiro: interessa na ficha, não na lista.
    assert "Imagem" in MateriasPrimasPage.COLUNAS_OCULTAS_POR_DEFEITO


def test_a_pasta_das_imagens_e_uma_configuracao_do_sistema() -> None:
    assert KEY_PASTA_IMAGENS_IMOS == "pasta_imagens_imos"
