"""Dialog for browsing the read-only server folders of a production process."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)

from app.services.producao_pastas_service import ArvorePastasProcesso


class PastasProcessoDialog(QDialog):
    """Show the server folder tree for one production process."""

    def __init__(
        self,
        *,
        codigo_processo: str,
        root_path: str,
        arvore: ArvorePastasProcesso,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.root_path = root_path
        self.arvore = arvore

        self.setWindowTitle(f"Pastas do processo - {codigo_processo}")
        self.setModal(True)
        self.setMinimumSize(760, 520)

        self.root_label = QLabel(root_path or "Caminho base de produção não configurado")
        self.root_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.root_label.setWordWrap(True)

        self.status_label = QLabel(self._mensagem_estado())
        self.status_label.setWordWrap(True)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Pasta"])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self._abrir_pasta)
        self.tree.itemSelectionChanged.connect(self._atualizar_botao_abrir)

        self.open_button = QPushButton("Abrir no explorador")
        self.open_button.setToolTip("Abrir a pasta selecionada no explorador")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._abrir_pasta_selecionada)

        self.close_button = QPushButton("Fechar")
        self.close_button.setToolTip("Fechar a janela de pastas")
        self.close_button.clicked.connect(self.accept)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.open_button)
        buttons_layout.addWidget(self.close_button)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Caminho"))
        layout.addWidget(self.root_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tree, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._preencher_arvore()

    def _mensagem_estado(self) -> str:
        if not self.root_path:
            return "Configure o caminho base de produção nas Configurações."
        if not self.arvore:
            return "Sem pastas no servidor para este processo."
        return ""

    def _preencher_arvore(self) -> None:
        self.tree.clear()
        if not self.root_path:
            return

        root = Path(self.root_path)
        for pasta_pai, versoes_obra in self.arvore.items():
            pai_path = root / pasta_pai
            pai_item = self._item(pasta_pai, pai_path)
            self.tree.addTopLevelItem(pai_item)

            for versao_obra, versoes_cutrite in versoes_obra.items():
                obra_path = pai_path / versao_obra
                obra_item = self._item(versao_obra, obra_path)
                pai_item.addChild(obra_item)

                for versao_cutrite in versoes_cutrite:
                    cutrite_path = obra_path / versao_cutrite
                    obra_item.addChild(self._item(versao_cutrite, cutrite_path))

        self.tree.expandAll()

    def _item(self, nome: str, caminho: Path) -> QTreeWidgetItem:
        item = QTreeWidgetItem([nome])
        item.setData(0, Qt.ItemDataRole.UserRole, str(caminho))
        item.setToolTip(0, str(caminho))
        return item

    def _abrir_pasta(self, item: QTreeWidgetItem, _column: int) -> None:
        caminho = self._caminho_item(item)
        if caminho:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(caminho)))

    def _abrir_pasta_selecionada(self) -> None:
        item = self.tree.currentItem()
        if item is not None:
            self._abrir_pasta(item, 0)

    def _atualizar_botao_abrir(self) -> None:
        self.open_button.setEnabled(self.tree.currentItem() is not None)

    def _caminho_item(self, item: QTreeWidgetItem) -> str:
        if not self.root_path:
            return ""

        partes: list[str] = []
        atual: QTreeWidgetItem | None = item
        while atual is not None:
            partes.append(atual.text(0))
            atual = atual.parent()

        return str(Path(self.root_path).joinpath(*reversed(partes)))
