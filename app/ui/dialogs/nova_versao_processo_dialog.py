"""Dialog for creating a new production process version."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


class NovaVersaoProcessoDialog(QDialog):
    """Choose version numbers for a new production process version."""

    def __init__(
        self,
        *,
        versao_obra_sug_cutrite: str,
        versao_plano_sug_cutrite: str,
        versao_obra_sug_obra: str,
        versao_plano_sug_obra: str,
        existing_keys: set[tuple[str, str]] | None = None,
        folder_root: str | None = None,
        folder_tree: dict[str, dict[str, list[str]]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nova Versão")
        self.resize(620, 520)

        self._sug_cutrite = (
            self._norm_two_digits(versao_obra_sug_cutrite),
            self._norm_two_digits(versao_plano_sug_cutrite),
        )
        self._sug_obra = (
            self._norm_two_digits(versao_obra_sug_obra),
            self._norm_two_digits(versao_plano_sug_obra),
        )
        self._existing_keys = {
            (self._norm_two_digits(vv), self._norm_two_digits(pp))
            for vv, pp in (existing_keys or set())
        }

        intro = QLabel(
            "Escolha a versão de obra e a versão CUT-RITE para o novo processo."
        )
        intro.setWordWrap(True)

        self.btn_sug_cutrite = QPushButton("Sugestão CUT-RITE")
        self.btn_sug_cutrite.setToolTip(
            "Usar a próxima versão CUT-RITE dentro da obra atual"
        )
        self.btn_sug_cutrite.clicked.connect(
            lambda: self._apply(*self._sug_cutrite)
        )
        self.btn_sug_obra = QPushButton("Sugestão Obra")
        self.btn_sug_obra.setToolTip(
            "Usar a próxima versão de obra, começando no CUT-RITE 01"
        )
        self.btn_sug_obra.clicked.connect(lambda: self._apply(*self._sug_obra))

        suggestions_layout = QHBoxLayout()
        suggestions_layout.addWidget(self.btn_sug_cutrite)
        suggestions_layout.addWidget(self.btn_sug_obra)
        suggestions_layout.addStretch()

        self.ed_ver_obra = QLineEdit()
        self.ed_ver_obra.setMaxLength(2)
        self.ed_ver_obra.setFixedWidth(70)
        self.ed_ver_obra.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ed_ver_obra.setValidator(QIntValidator(1, 99, self))
        self.ed_ver_obra.setToolTip("Versão da obra (01 a 99)")

        self.ed_ver_plano = QLineEdit()
        self.ed_ver_plano.setMaxLength(2)
        self.ed_ver_plano.setFixedWidth(70)
        self.ed_ver_plano.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ed_ver_plano.setValidator(QIntValidator(1, 99, self))
        self.ed_ver_plano.setToolTip("Versão CUT-RITE (01 a 99)")

        for line in (self.ed_ver_obra, self.ed_ver_plano):
            line.textChanged.connect(self._refresh_status)
            line.editingFinished.connect(self._format_inputs)

        form = QFormLayout()
        form.addRow("Versão obra", self.ed_ver_obra)
        form.addRow("Versão CUT-RITE", self.ed_ver_plano)

        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet("color: #B00020; font-weight: bold;")
        self.warning_label.setWordWrap(True)

        folder_group = QGroupBox("Pastas existentes (Servidor)")
        folder_layout = QVBoxLayout(folder_group)
        self.folder_root_label = QLabel(folder_root or "")
        self.folder_root_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        self.folder_root_label.setWordWrap(True)
        folder_layout.addWidget(self.folder_root_label)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        folder_layout.addWidget(self.tree, stretch=1)
        self._populate_tree(folder_tree or {})

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Criar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Cancelar"
        )
        self.button_box.accepted.connect(self._on_accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addLayout(suggestions_layout)
        layout.addLayout(form)
        layout.addWidget(self.warning_label)
        layout.addWidget(folder_group, stretch=1)
        layout.addWidget(self.button_box)

        self._apply(*self._sug_cutrite)

    def values(self) -> tuple[str, str]:
        """Return the selected (versao_obra, versao_plano) pair."""
        return (
            self._norm_two_digits(self.ed_ver_obra.text()),
            self._norm_two_digits(self.ed_ver_plano.text()),
        )

    def _populate_tree(self, folder_tree: dict[str, dict[str, list[str]]]) -> None:
        self.tree.clear()
        if not folder_tree:
            item = QTreeWidgetItem(["Sem pastas existentes para este processo"])
            item.setDisabled(True)
            self.tree.addTopLevelItem(item)
            return

        for pai, versoes_obra in sorted(folder_tree.items(), key=lambda item: item[0].casefold()):
            pai_item = QTreeWidgetItem([pai])
            self.tree.addTopLevelItem(pai_item)
            for versao_obra, versoes_plano in sorted(
                versoes_obra.items(),
                key=lambda item: item[0].casefold(),
            ):
                obra_item = QTreeWidgetItem([versao_obra])
                pai_item.addChild(obra_item)
                for versao_plano in sorted(versoes_plano, key=str.casefold):
                    obra_item.addChild(QTreeWidgetItem([versao_plano]))
        self.tree.expandAll()

    def _apply(self, versao_obra: str, versao_plano: str) -> None:
        self.ed_ver_obra.setText(self._norm_two_digits(versao_obra))
        self.ed_ver_plano.setText(self._norm_two_digits(versao_plano))
        self._refresh_status()

    def _format_inputs(self) -> None:
        for line in (self.ed_ver_obra, self.ed_ver_plano):
            text = line.text().strip()
            if text:
                line.setText(self._norm_two_digits(text))
        self._refresh_status()

    def _refresh_status(self) -> None:
        vv, pp = self.values()
        duplicate = bool(vv and pp and (vv, pp) in self._existing_keys)
        if duplicate:
            self.warning_label.setText(
                f"A versão {vv}/{pp} já existe na BD ou nas pastas do servidor."
            )
        else:
            self.warning_label.clear()
        self.ok_button.setEnabled(bool(vv and pp) and not duplicate)

    def _on_accept(self) -> None:
        self._format_inputs()
        vv, pp = self.values()
        if not vv or not pp:
            QMessageBox.warning(self, "Nova Versão", "Preencha as duas versões.")
            return
        if (vv, pp) in self._existing_keys:
            QMessageBox.warning(
                self,
                "Nova Versão",
                f"A versão {vv}/{pp} já existe.",
            )
            return
        self.accept()

    @staticmethod
    def _norm_two_digits(value) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        if text.isdigit():
            return f"{int(text):02d}"
        return text[:2] if len(text) >= 2 else text.zfill(2)
