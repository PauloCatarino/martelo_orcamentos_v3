"""Read-only dialog showing a module's structural lines (phase 8U.3).

Mirrors the preview panel of the import dialog (image + name + description +
the module's lines), used by the library-management page's "Ver linhas".
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.domain.modulo_categorias import get_modulo_categoria_label


class ModuloLinhasDialog(QDialog):
    """Read-only preview of a saved module (header + structural lines)."""

    _COLUNAS = (
        "Tipo",
        "Código/Def. peça",
        "Descrição",
        "Prioridade",
        "QT",
        "Comp",
        "Larg",
        "Esp",
    )
    _LARGURAS = (130, 140, 200, 75, 50, 60, 60, 60)
    _TAMANHO_IMAGEM = 180

    def __init__(self, parent=None, *, modulo=None, linhas: Sequence | None = None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Linhas do Módulo")
        self.setModal(True)
        self.setMinimumSize(680, 460)

        self.imagem_label = QLabel("Sem imagem")
        self.imagem_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.imagem_label.setFixedHeight(self._TAMANHO_IMAGEM)
        self.imagem_label.setStyleSheet(
            "QLabel { border: 1px solid #c0c0c0; background: #f5f5f5; }"
        )

        self.nome_label = QLabel("")
        self.nome_label.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.nome_label.setWordWrap(True)

        self.descricao_view = QPlainTextEdit()
        self.descricao_view.setReadOnly(True)
        self.descricao_view.setMaximumHeight(70)

        self.tabela = QTableWidget(0, len(self._COLUNAS))
        self.tabela.setHorizontalHeaderLabels(self._COLUNAS)
        self.tabela.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabela.verticalHeader().setVisible(False)
        header = self.tabela.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        for indice, largura in enumerate(self._LARGURAS):
            self.tabela.setColumnWidth(indice, largura)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.button(QDialogButtonBox.StandardButton.Close).setText("Fechar")
        self.button_box.rejected.connect(self.reject)
        self.button_box.accepted.connect(self.accept)
        self.button_box.clicked.connect(lambda _btn: self.accept())

        layout = QVBoxLayout()
        layout.addWidget(self.imagem_label)
        layout.addWidget(self.nome_label)
        layout.addWidget(self.descricao_view)
        layout.addWidget(QLabel("Linhas do módulo"))
        layout.addWidget(self.tabela, stretch=1)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        if modulo is not None:
            self._mostrar(modulo, linhas or [])

    def _mostrar(self, modulo, linhas: Sequence) -> None:
        self._mostrar_imagem(modulo.imagem_path)
        nome = modulo.nome or modulo.codigo or ""
        categoria = get_modulo_categoria_label(modulo.categoria)
        self.nome_label.setText(f"{modulo.codigo} — {nome}  ({categoria})")
        self.descricao_view.setPlainText(modulo.descricao or "")

        self.tabela.setRowCount(0)
        for linha in linhas:
            row = self.tabela.rowCount()
            self.tabela.insertRow(row)
            qt = linha.qt_und or linha.qt_mod or ""
            valores = (
                linha.tipo_linha or "",
                linha.def_peca_codigo or linha.codigo or "",
                linha.descricao or linha.descricao_livre or "",
                str(linha.prioridade_valueset or ""),
                str(qt),
                linha.comp or "",
                linha.larg or "",
                linha.esp or "",
            )
            for col, texto in enumerate(valores):
                self.tabela.setItem(row, col, QTableWidgetItem(texto))

    def _mostrar_imagem(self, caminho: str | None) -> None:
        if caminho:
            pixmap = QPixmap(caminho)
            if not pixmap.isNull():
                self.imagem_label.setText("")
                self.imagem_label.setPixmap(
                    pixmap.scaled(
                        self._TAMANHO_IMAGEM,
                        self._TAMANHO_IMAGEM,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                )
                return
        self.imagem_label.setText("Sem imagem")
        self.imagem_label.setPixmap(QPixmap())
