"""Runtime checks for persistent column widths."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QHeaderView, QTreeWidget

from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


def test_larguras_colunas_suporta_tree_widget() -> None:
    app = QApplication.instance() or QApplication([])
    tree = QTreeWidget()
    tree.setColumnCount(2)
    tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)

    resultado = ligar_persistencia_larguras(tree, "teste_tree_widget")

    assert isinstance(resultado, bool)
    assert tree.header().count() == 2
    tree.deleteLater()
    app.processEvents()
