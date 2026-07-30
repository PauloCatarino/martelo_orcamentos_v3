"""Realce da célula sob o rato nas listas."""

from __future__ import annotations

import sys

import pytest


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _opcao_e_indice(cor_propria=None):
    from PySide6.QtGui import QBrush, QColor
    from PySide6.QtWidgets import QStyleOptionViewItem, QTableWidget, QTableWidgetItem

    tabela = QTableWidget(1, 1)
    item = QTableWidgetItem("WERNAGEN")
    if cor_propria is not None:
        item.setBackground(QBrush(QColor(cor_propria)))
    tabela.setItem(0, 0, item)

    return QStyleOptionViewItem(), tabela.model().index(0, 0), tabela


def test_celula_sob_o_rato_fica_castanha_com_texto_branco(_app) -> None:
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import QStyle

    from app.ui import tema
    from app.ui.widgets.realce_rato_delegate import TEXTO_REALCE, RealceRatoDelegate

    opcao, indice, _tabela = _opcao_e_indice()
    opcao.state |= QStyle.StateFlag.State_MouseOver

    RealceRatoDelegate().initStyleOption(opcao, indice)

    assert opcao.backgroundBrush.color() == QColor(tema.CASTANHO_ESCURO)
    assert opcao.palette.color(QPalette.ColorRole.Text) == QColor(TEXTO_REALCE)


def test_realce_ganha_a_cor_propria_da_celula(_app) -> None:
    """As células marcadas (simplex vazio/longo) também acendem ao passar."""
    from PySide6.QtGui import QColor
    from PySide6.QtWidgets import QStyle

    from app.ui import tema
    from app.ui.widgets.realce_rato_delegate import RealceRatoDelegate

    opcao, indice, _tabela = _opcao_e_indice(cor_propria=tema.VERMELHO_SUAVE)
    opcao.state |= QStyle.StateFlag.State_MouseOver

    RealceRatoDelegate().initStyleOption(opcao, indice)

    assert opcao.backgroundBrush.color() == QColor(tema.CASTANHO_ESCURO)


def test_sem_rato_por_cima_nao_mexe_nas_cores(_app) -> None:
    from PySide6.QtGui import QColor

    from app.ui import tema
    from app.ui.widgets.realce_rato_delegate import RealceRatoDelegate

    opcao, indice, _tabela = _opcao_e_indice(cor_propria=tema.VERMELHO_SUAVE)

    RealceRatoDelegate().initStyleOption(opcao, indice)

    assert opcao.backgroundBrush.color() == QColor(tema.VERMELHO_SUAVE)
