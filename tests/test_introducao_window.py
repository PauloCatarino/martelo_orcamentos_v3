from __future__ import annotations

from PySide6.QtWidgets import QApplication

from app.ui.introducao_window import IntroducaoWindow


def test_introducao_e_curta_ignoravel_e_idempotente() -> None:
    app = QApplication.instance() or QApplication([])
    janela = IntroducaoWindow("Paulo")
    sinais = []
    janela.concluida.connect(lambda: sinais.append(True))
    assert "Paulo" in janela.saudacao_label.text()
    janela.terminar(); janela.terminar()
    assert sinais == [True]
    app.processEvents()


def test_introducao_marca_aplicacao_pronta() -> None:
    app = QApplication.instance() or QApplication([])
    janela = IntroducaoWindow()
    janela.marcar_aplicacao_pronta()
    assert janela.progresso.value() == 100
    assert "pronto" in janela.etapa_label.text().casefold()
    janela.terminar(); app.processEvents()


class _WidgetMorto:
    """Stand-in for a widget whose C++ side was already deleted."""

    def setText(self, _texto):  # noqa: N802 (Qt)
        raise RuntimeError(
            "Internal C++ object (PySide6.QtWidgets.QLabel) already deleted."
        )

    def setValue(self, _valor):  # noqa: N802 (Qt)
        raise RuntimeError(
            "Internal C++ object (PySide6.QtWidgets.QProgressBar) already deleted."
        )


def test_pagina_que_acaba_de_carregar_depois_do_ignorar_e_ignorada() -> None:
    """Ignorar fecha a janela; o preload do Ponto Situação só avisa depois."""
    app = QApplication.instance() or QApplication([])
    janela = IntroducaoWindow()
    janela.terminar()

    janela.marcar_aplicacao_pronta()

    assert janela.progresso.value() != 100
    app.processEvents()


def test_janela_ja_destruida_nao_rebenta_o_arranque() -> None:
    """Rede de segurança: o C++ pode desaparecer sem passar por terminar()."""
    app = QApplication.instance() or QApplication([])
    janela = IntroducaoWindow()
    janela.etapa_label = _WidgetMorto()
    janela.progresso = _WidgetMorto()

    janela.marcar_aplicacao_pronta()
    janela._avancar()

    assert janela._terminou is True
    app.processEvents()


def test_introducao_mantem_tres_segundos_minimos() -> None:
    import inspect

    source = inspect.getsource(IntroducaoWindow.marcar_aplicacao_pronta)
    assert "3000 - self._relogio.elapsed()" in source
