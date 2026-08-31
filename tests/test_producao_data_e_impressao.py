"""Três pedidos do Paulo no menu Produção (2026-08-31).

1. A Data Início, estando vazia, deve começar em HOJE quando se vai escolher.
2. O Caderno de Encargos da produção tem de vir já com o visto do Duplex.
3. A pré-visualização do diálogo de impressão tem de poder crescer.
"""

from __future__ import annotations

import inspect
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate, QEvent, QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent
from PySide6.QtWidgets import QApplication

from app.services.producao_impressao_service import (
    DOCUMENTOS_DUPLEX_POR_DEFEITO,
    base_do_documento,
    chave_prioridade_documento,
    duplex_por_defeito,
)
from app.ui.pages.producao_page import DATA_VAZIA, CampoData

_app = QApplication.instance() or QApplication([])


# ----- 1. Data Início começa em hoje -----


def _campo_vazio() -> CampoData:
    campo = CampoData()
    campo.setDisplayFormat("dd-MM-yyyy")
    campo.setCalendarPopup(True)
    campo.setMinimumDate(DATA_VAZIA)
    campo.setSpecialValueText(" ")
    campo.setDate(DATA_VAZIA)
    campo.resize(200, 24)
    return campo


def _clicar(campo: CampoData, x: int) -> None:
    campo.mousePressEvent(
        QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(x, 12),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
    )


def test_clicar_na_setinha_com_o_campo_vazio_comeca_em_hoje() -> None:
    campo = _campo_vazio()

    _clicar(campo, 190)  # a setinha do calendário, à direita

    assert campo.date() == QDate.currentDate()


def test_clicar_no_meio_do_campo_nao_preenche_data_nenhuma() -> None:
    """Senão bastava passar por um processo para lhe nascer uma data."""
    campo = _campo_vazio()

    _clicar(campo, 60)

    assert campo.date() == DATA_VAZIA


@pytest.mark.parametrize(
    "tecla",
    [Qt.Key.Key_Down, Qt.Key.Key_Up, Qt.Key.Key_F4, Qt.Key.Key_PageDown],
)
def test_as_teclas_de_escolher_data_comecam_em_hoje(tecla) -> None:
    campo = _campo_vazio()

    campo.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, tecla, Qt.KeyboardModifier.NoModifier)
    )

    assert campo.date() == QDate.currentDate()


def test_campo_com_data_nao_e_mexido() -> None:
    campo = _campo_vazio()
    campo.setDate(QDate(2026, 3, 15))

    _clicar(campo, 190)
    campo.keyPressEvent(
        QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Down, Qt.KeyboardModifier.NoModifier)
    )

    # A seta continua a andar um dia, como sempre fez — o que não pode é saltar
    # para hoje e apagar o que lá estava.
    assert campo.date().year() == 2026
    assert campo.date().month() == 3


def test_a_pagina_usa_o_campo_novo() -> None:
    from app.ui.pages.producao_page import ProducaoPage

    fonte = inspect.getsource(ProducaoPage._campo_data)
    assert "CampoData()" in fonte


# ----- 2. Duplex do Caderno de Encargos da produção -----


def test_o_caderno_de_encargos_da_producao_vem_com_duplex() -> None:
    assert duplex_por_defeito("1_Producao_CE_1403_01_01_JF_VIVA.pdf") is True


@pytest.mark.parametrize(
    "nome",
    [
        "1_Ferragem_CE_1403_01_01_JF_VIVA.pdf",
        "1_Cliente_CE_1403_01_01_JF_VIVA.pdf",
        "1_Montagem_CE_1403_01_01_JF_VIVA.pdf",
        "1_Projeto_CE_1403_01_01_JF_VIVA.pdf",
        "1403_01_01_26_JF_VIVA.pdf",
        "6_Resumo_ML_OrlasA4.pdf",
        "2_Projeto_Producao.pdf",
        "5_Etiqueta_Palete.pdf",
        "CONJ.pdf",
        "RP_06(a).pdf",
        "",
    ],
)
def test_os_outros_documentos_nao_vem_com_duplex(nome: str) -> None:
    """Só o Caderno de Encargos da produção; os outros gastavam papel a mais."""
    assert duplex_por_defeito(nome) is False


def test_o_duplex_nao_depende_da_obra_nem_do_cliente() -> None:
    """A mesma regra tem de servir na obra seguinte."""
    for nome in (
        "1_Producao_CE_1403_01_01_JF_VIVA.pdf",
        "1_Producao_CE_1500_02_01_INNERE.pdf",
        "1_Producao_CE.pdf",
    ):
        assert duplex_por_defeito(nome) is True


def test_a_base_do_documento_tira_a_obra_e_o_cliente() -> None:
    assert base_do_documento("1_Producao_CE_1403_01_01_JF_VIVA.pdf") == "1_producao_ce"
    assert base_do_documento("6_Resumo_ML_OrlasA4.pdf") == "6_resumo_ml_orlasa4"


def test_a_chave_da_ordem_continua_a_dar_o_mesmo() -> None:
    """A base foi separada da chave; a chave não pode ter mudado de forma."""
    assert chave_prioridade_documento(
        "1_Producao_CE_1403_01_01_JF_VIVA.pdf", "CADERNO ENCARGOS"
    ) == "documento:CADERNO ENCARGOS:1_producao_ce"
    assert chave_prioridade_documento("", "OUTROS") == "documento:OUTROS:sem_nome"


def test_a_lista_do_duplex_esta_em_minusculas() -> None:
    """A comparação é com a base, que vem sempre em minúsculas."""
    assert all(nome == nome.casefold() for nome in DOCUMENTOS_DUPLEX_POR_DEFEITO)


# ----- 3. A pré-visualização pode crescer -----


def test_o_dialogo_tem_divisoria_arrastavel() -> None:
    from app.ui.dialogs.producao_impressao_dialog import ProducaoImpressaoDialog

    fonte = inspect.getsource(ProducaoImpressaoDialog.__init__)
    assert "QSplitter" in fonte
    # A altura fixa que travava a pré-visualização tem de ter desaparecido.
    assert "setMaximumHeight(280)" not in fonte
    # E a lista não pode poder ser encolhida até desaparecer.
    assert "setChildrenCollapsible(False)" in fonte


def test_a_altura_escolhida_fica_guardada_por_utilizador() -> None:
    from app.ui.dialogs.producao_impressao_dialog import ProducaoImpressaoDialog

    guardar = inspect.getsource(ProducaoImpressaoDialog._guardar_alturas)
    ler = inspect.getsource(ProducaoImpressaoDialog._altura_guardada)
    assert "UserPrefService" in guardar
    assert "UserPrefService" in ler
    assert "self._user_id" in guardar
    # Não vale a pena estragar uma impressão por não se conseguir gravar isto.
    assert "except" in guardar
