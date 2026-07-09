"""Regression test: every static QSS stylesheet in the app must parse cleanly.

An unbalanced-brace typo in an f-string/string concatenation (extra or
missing ``{``/``}``, a literal ``{NOME_CONSTANTE}`` left unsubstituted
because the string was missing its ``f`` prefix, mismatched quotes, ...)
does not raise a Python exception -- Qt just logs
"Could not parse stylesheet of object ..." at runtime and silently drops
the broken rule (and everything after it). This test applies every QSS
constant of the theme -- and the composed stylesheet the 3 ValueSet
tables actually apply via ``configurar_tabela_valueset`` -- to a real
widget and fails if Qt's message handler reports a parse error.
"""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from collections.abc import Callable

import pytest
from PySide6.QtCore import qInstallMessageHandler
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QTableWidget,
    QTabWidget,
    QTreeWidget,
)

from app.ui import tema
from app.ui.widgets.estilo_tabela_valueset import configurar_tabela_valueset

_app = QApplication.instance() or QApplication([])


def _sem_aviso_qss(aplicar: Callable[[], None]) -> None:
    """Run ``aplicar`` (which must trigger setStyleSheet) and fail on any QSS parse warning."""
    capturados: list[str] = []
    anterior = qInstallMessageHandler(
        lambda _tipo, _contexto, mensagem: capturados.append(mensagem)
    )
    try:
        aplicar()
        _app.processEvents()
    finally:
        qInstallMessageHandler(anterior)

    avisos_qss = [mensagem for mensagem in capturados if "Could not parse stylesheet" in mensagem]
    assert not avisos_qss, f"QSS inválida: {avisos_qss}"


def _criar_nav_tree() -> QTreeWidget:
    """Match the real widget: main_window applies ESTILO_ARVORE_NAV to #navTree."""
    tree = QTreeWidget()
    tree.setObjectName("navTree")
    return tree


@pytest.mark.parametrize(
    "nome_constante,criar_widget",
    [
        ("ESTILO_TABELA_CONFIG", lambda: QTableWidget(1, 1)),
        ("ESTILO_TABELA_CONFIG_CABECALHO", lambda: QTableWidget(1, 1)),
        ("ESTILO_ABAS", QTabWidget),
        ("ESTILO_SIDEBAR", QPushButton),
        ("ESTILO_ARVORE_NAV", _criar_nav_tree),
    ],
)
def test_constante_qss_do_tema_e_valida(nome_constante, criar_widget) -> None:
    """Every named QSS constant in app.ui.tema must parse without warnings."""
    qss = getattr(tema, nome_constante)
    widget = criar_widget()

    _sem_aviso_qss(lambda: widget.setStyleSheet(qss))


def test_qss_composta_das_tabelas_valueset_e_valida() -> None:
    """The exact stylesheet the 3 ValueSet tables apply (modelo/orçamento/item)."""
    table = QTableWidget(1, 1)

    _sem_aviso_qss(lambda: configurar_tabela_valueset(table, "teste_regressao_qss"))
