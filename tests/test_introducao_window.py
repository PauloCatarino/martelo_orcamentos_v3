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


def test_introducao_mantem_tres_segundos_minimos() -> None:
    import inspect

    source = inspect.getsource(IntroducaoWindow.marcar_aplicacao_pronta)
    assert "3000 - self._relogio.elapsed()" in source
