"""Mudar de utilizador para os relógios da janela de quem sai (19-10-2026).

Visto no terminal: o Paulo mudou para a Catia e, sete minutos depois, com a
janela dele já fechada e ainda sem ninguém entrado, o relógio do Assistente dos
Orçamentos dele deu horas e falhou («Could not locate a bind…»). Depois de a
Catia entrar, o mesmo relógio corria com a ligação dela.
"""

from __future__ import annotations

import inspect
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QWidget

from app.ui import main_window
from app.ui.main_window import parar_relogios


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


def test_para_os_relogios_dos_avisos_da_janela(_app) -> None:
    janela = QWidget()
    aviso = QObject(janela)  # como o Assistente, filho da janela
    relogio_aviso = QTimer(aviso)
    relogio_aviso.start(10 * 60 * 1000)
    relogio_da_janela = QTimer(janela)
    relogio_da_janela.start(60 * 1000)
    parado_antes = QTimer(janela)

    assert parar_relogios(janela) == 2

    assert not relogio_aviso.isActive()
    assert not relogio_da_janela.isActive()
    assert not parado_antes.isActive()
    janela.deleteLater()


def test_relogios_de_outra_janela_continuam(_app) -> None:
    janela_que_sai = QWidget()
    janela_nova = QWidget()
    relogio_novo = QTimer(QObject(janela_nova))
    relogio_novo.start(60 * 1000)

    parar_relogios(janela_que_sai)

    assert relogio_novo.isActive()
    relogio_novo.stop()
    janela_que_sai.deleteLater()
    janela_nova.deleteLater()


def test_fechar_a_janela_principal_para_os_relogios() -> None:
    fonte = inspect.getsource(main_window.MainWindow.closeEvent)

    assert "parar_relogios(self)" in fonte
    # Só depois de a página deixar sair: se a pessoa cancelar, fica tudo a correr.
    assert fonte.index("pode_sair()") < fonte.index("parar_relogios(self)")
