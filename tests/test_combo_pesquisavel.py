"""Filtro «Cliente» onde se escreve (pedido do Paulo, 01-10-2026).

Com centenas de clientes, encontrar um na lista obrigava a rolar a barra.
Agora escreve-se parte do nome e aparecem as sugestões; a lista de obras só
muda quando se escolhe um cliente, nunca a meio da escrita.
"""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("PySide6")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from app.ui.widgets.combo_sem_scroll import ComboPesquisavel, ComboSemScroll  # noqa: E402

CLIENTES = ["Todos", "MÓVEIS J.F. VIVA", "CREAHOME", "TEMPO PLURAL", "TEMPO LIVRE"]


@pytest.fixture(scope="module")
def app():
    aplicacao = QApplication.instance() or QApplication([])
    yield aplicacao


@pytest.fixture
def combo(app):
    campo = ComboPesquisavel()
    campo.addItems(CLIENTES)
    campo.escolhas = []
    campo.currentIndexChanged.connect(lambda _i: campo.escolhas.append(campo.currentText()))
    campo.show()
    campo.lineEdit().setFocus()
    app.processEvents()
    yield campo
    campo.close()


def _escrever(app, combo, texto):
    combo.lineEdit().selectAll()
    QTest.keyClicks(combo.lineEdit(), texto)
    for _ in range(3):
        app.processEvents()


def _sugestoes(combo):
    modelo = combo.completer().popup().model()
    return [modelo.index(r, 0).data() for r in range(modelo.rowCount())]


def test_continua_a_ser_um_dropdown_sem_roda():
    assert issubclass(ComboPesquisavel, ComboSemScroll)


def test_sugere_sem_acentos_nem_pontuacao_e_nao_filtra_a_meio(app, combo):
    _escrever(app, combo, "jf viva")
    assert _sugestoes(combo) == ["MÓVEIS J.F. VIVA"]
    # A meio da escrita a escolha não mudou: a lista de obras não mexe.
    assert combo.currentText() == "Todos"
    assert combo.escolhas == []


def test_enter_com_uma_so_sugestao_escolhe_essa(app, combo):
    _escrever(app, combo, "moveis")
    QTest.keyClick(combo.lineEdit(), Qt.Key.Key_Return)
    app.processEvents()
    assert combo.currentText() == "MÓVEIS J.F. VIVA"
    assert combo.lineEdit().text() == "MÓVEIS J.F. VIVA"
    assert combo.escolhas == ["MÓVEIS J.F. VIVA"]


def test_escolher_com_as_setas_na_lista_de_sugestoes(app, combo):
    _escrever(app, combo, "tempo")
    assert _sugestoes(combo) == ["TEMPO PLURAL", "TEMPO LIVRE"]
    popup = combo.completer().popup()
    QTest.keyClick(popup, Qt.Key.Key_Down)
    QTest.keyClick(popup, Qt.Key.Key_Down)
    QTest.keyClick(popup, Qt.Key.Key_Return)
    for _ in range(3):
        app.processEvents()
    assert combo.currentText() == "TEMPO LIVRE"
    assert combo.lineEdit().text() == "TEMPO LIVRE"


def test_clique_numa_sugestao(app, combo):
    _escrever(app, combo, "crea")
    popup = combo.completer().popup()
    linha = popup.visualRect(popup.model().index(0, 0)).center()
    QTest.mouseClick(popup.viewport(), Qt.MouseButton.LeftButton, pos=linha)
    for _ in range(3):
        app.processEvents()
    assert combo.currentText() == "CREAHOME"


def test_varias_sugestoes_e_enter_reabre_a_lista_sem_mudar(app, combo):
    _escrever(app, combo, "tempo")
    combo.completer().popup().hide()
    QTest.keyClick(combo.lineEdit(), Qt.Key.Key_Return)
    app.processEvents()
    assert combo.currentText() == "Todos"
    assert combo.completer().popup().isVisible()


def test_texto_sem_cliente_volta_ao_que_estava(app, combo):
    combo.setCurrentText("CREAHOME")
    _escrever(app, combo, "xyz")
    combo.completer().popup().hide()
    combo.lineEdit().clearFocus()
    app.processEvents()
    assert combo.currentText() == "CREAHOME"
    assert combo.lineEdit().text() == "CREAHOME"


def test_apagar_tudo_e_enter_volta_a_todos(app, combo):
    combo.setCurrentText("CREAHOME")
    combo.lineEdit().selectAll()
    QTest.keyClick(combo.lineEdit(), Qt.Key.Key_Delete)
    QTest.keyClick(combo.lineEdit(), Qt.Key.Key_Return)
    app.processEvents()
    assert combo.currentText() == "Todos"


def test_escape_desfaz_o_que_se_escreveu(app, combo):
    combo.setCurrentText("CREAHOME")
    _escrever(app, combo, "temp")
    combo.completer().popup().hide()
    QTest.keyClick(combo.lineEdit(), Qt.Key.Key_Escape)
    assert combo.lineEdit().text() == "CREAHOME"
    assert combo.currentText() == "CREAHOME"


def test_set_current_text_escolhe_como_um_dropdown_normal(app, combo):
    combo.setCurrentText("TEMPO PLURAL")
    assert combo.currentText() == "TEMPO PLURAL"
    assert combo.currentIndex() == 3
    combo.setCurrentText("NÃO EXISTE")
    assert combo.currentText() == "TEMPO PLURAL"


@pytest.mark.parametrize(
    "modulo",
    [
        "app.ui.pages.orcamentos_page",
        "app.ui.pages.producao_page",
        "app.ui.pages.ponto_situacao_page",
        "app.ui.pages.inicio_page",
    ],
)
def test_os_quatro_menus_usam_o_cliente_onde_se_escreve(modulo):
    import importlib
    import re

    fonte = inspect.getsource(importlib.import_module(modulo))
    assert "self.cliente_combo = ComboPesquisavel()" in fonte
    # Ligado à escolha, não a cada tecla.
    assert "self.cliente_combo.currentIndexChanged.connect(" in fonte
    assert "cliente_combo.currentTextChanged" not in fonte
    assert not re.search(
        r"for combo in \([^)]*self\.cliente_combo[^)]*\):\s*\n\s*combo\.currentTextChanged",
        fonte,
    )
