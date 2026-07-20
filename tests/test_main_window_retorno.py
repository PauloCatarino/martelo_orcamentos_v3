"""Banner de "voltar": regressar ao custeio depois de o assistente enviar a um menu."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QFrame, QLabel, QStackedWidget, QWidget

from app.ui.main_window import MainWindow

_app = QApplication.instance() or QApplication([])


class _FakeWin:
    """Reaproveita os métodos reais de navegação da MainWindow, sem DB/janela."""

    _ROTULO_RETORNO = MainWindow._ROTULO_RETORNO
    navegar_para_resolver = MainWindow.navegar_para_resolver
    _voltar_resolver = MainWindow._voltar_resolver
    _pagina_atual_nome = MainWindow._pagina_atual_nome
    _esconder_banner_retorno = MainWindow._esconder_banner_retorno

    def __init__(self) -> None:
        self.pages = QStackedWidget()
        self.pages.addWidget(QWidget())  # 0: orcamento_detail
        self.pages.addWidget(QWidget())  # 1: materias_primas
        self._page_indexes = {"orcamento_detail": 0, "materias_primas": 1}
        self._retorno_banner = QFrame()
        self._retorno_label = QLabel()
        self._retorno_resolver = None
        self.mostradas: list[str] = []

    def show_page(self, name: str) -> None:
        self.mostradas.append(name)
        self.pages.setCurrentIndex(self._page_indexes[name])


def test_navegar_para_resolver_guarda_origem_e_mostra_banner() -> None:
    win = _FakeWin()
    win.show_page("orcamento_detail")

    win.navegar_para_resolver("materias_primas")

    assert win.mostradas[-1] == "materias_primas"
    assert win._retorno_resolver == "orcamento_detail"
    assert not win._retorno_banner.isHidden()  # banner visível
    assert win._retorno_label.text()  # tem texto de contexto


def test_voltar_resolver_regressa_e_esconde_banner() -> None:
    win = _FakeWin()
    win.show_page("orcamento_detail")
    win.navegar_para_resolver("materias_primas")

    win._voltar_resolver()

    assert win.mostradas[-1] == "orcamento_detail"  # regressou ao custeio
    assert win._retorno_resolver is None
    assert win._retorno_banner.isHidden()


def test_navegacao_manual_esconde_banner() -> None:
    win = _FakeWin()
    win.show_page("orcamento_detail")
    win.navegar_para_resolver("materias_primas")

    win._esconder_banner_retorno()

    assert win._retorno_resolver is None
    assert win._retorno_banner.isHidden()
