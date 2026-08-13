"""Runtime checks for persistent column widths."""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QHeaderView, QTableWidget, QTreeWidget

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


def test_persistencia_opcional_permite_reordenar_colunas(monkeypatch) -> None:
    app = QApplication.instance() or QApplication([])
    valores: dict[str, object] = {}

    class FakeSettings:
        def __init__(self, *_args) -> None:
            pass

        def value(self, chave: str):
            return valores.get(chave)

        def setValue(self, chave: str, valor) -> None:  # noqa: N802 (Qt API)
            valores[chave] = valor

    monkeypatch.setattr("app.ui.widgets.larguras_colunas.QSettings", FakeSettings)
    primeira = QTableWidget(0, 3)
    ligar_persistencia_larguras(primeira, "teste_ordem", guardar_ordem=True)
    primeira.horizontalHeader().moveSection(2, 0)

    segunda = QTableWidget(0, 3)
    restaurou = ligar_persistencia_larguras(
        segunda, "teste_ordem", guardar_ordem=True
    )

    assert restaurou is True
    assert segunda.horizontalHeader().sectionsMovable() is True
    assert [
        segunda.horizontalHeader().logicalIndex(posicao) for posicao in range(3)
    ] == [2, 0, 1]
    primeira.deleteLater()
    segunda.deleteLater()
    app.processEvents()
