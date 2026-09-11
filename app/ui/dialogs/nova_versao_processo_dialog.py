"""Dialog for creating a new production process version."""

from __future__ import annotations
from app.ui import tema

from PySide6.QtCore import Qt, QTimer
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
        streamlit_keys: set[tuple[str, str]] | None = None,
        folder_root: str | None = None,
        folder_tree: dict[str, dict[str, list[str]]] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Novo Modelo/Versão")
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
        self._streamlit_keys = streamlit_keys or set()
        self._existing_keys |= self._streamlit_keys

        intro = QLabel(
            "Escolha o Modelo e a Versão para o novo processo."
        )
        intro.setWordWrap(True)

        self.btn_sug_cutrite = QPushButton("Sugestão Versão")
        self.btn_sug_cutrite.setToolTip(
            "Usar a próxima Versão dentro do Modelo atual"
        )
        self.btn_sug_cutrite.clicked.connect(
            lambda: self._apply(*self._sug_cutrite)
        )
        self.btn_sug_obra = QPushButton("Sugestão Modelo")
        self.btn_sug_obra.setToolTip(
            "Usar o próximo Modelo, começando na Versão 01"
        )
        self.btn_sug_obra.clicked.connect(lambda: self._apply(*self._sug_obra))

        suggestions_layout = QHBoxLayout()
        suggestions_layout.addWidget(self.btn_sug_obra)
        suggestions_layout.addWidget(self.btn_sug_cutrite)
        suggestions_layout.addStretch()

        self.ed_ver_obra = QLineEdit()
        self.ed_ver_obra.setMaxLength(2)
        self.ed_ver_obra.setFixedWidth(70)
        self.ed_ver_obra.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ed_ver_obra.setValidator(QIntValidator(1, 99, self))
        self.ed_ver_obra.setToolTip("MODELO no IMOX IX (01 a 99)")

        self.ed_ver_plano = QLineEdit()
        self.ed_ver_plano.setMaxLength(2)
        self.ed_ver_plano.setFixedWidth(70)
        self.ed_ver_plano.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.ed_ver_plano.setValidator(QIntValidator(1, 99, self))
        self.ed_ver_plano.setToolTip("Versão CUT-RITE (01 a 99)")

        for line in (self.ed_ver_obra, self.ed_ver_plano):
            line.textChanged.connect(self._refresh_status)
            line.editingFinished.connect(self._format_inputs)

        self._blink_timer = QTimer(self)
        self._blink_timer.setInterval(350)
        self._blink_timer.timeout.connect(self._blink_tick)
        self._blink_on = False
        self._blink_base_styles = [
            (self.ed_ver_obra, self.ed_ver_obra.styleSheet()),
            (self.ed_ver_plano, self.ed_ver_plano.styleSheet()),
        ]

        form = QFormLayout()
        form.addRow("MODELO no IMOX IX", self.ed_ver_obra)
        form.addRow("Versão CUT-RITE", self.ed_ver_plano)

        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet(f"color: {tema.TEXTO_ERRO}; font-weight: bold;")
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
        if self._streamlit_keys:
            registos = QTreeWidgetItem(["Registos no Streamlit (com ou sem pasta)"])
            self.tree.addTopLevelItem(registos)
            for modelo in sorted({m for m, _ in self._streamlit_keys}):
                item = QTreeWidgetItem([f"Modelo {modelo}"])
                registos.addChild(item)
                for m, versao in sorted(self._streamlit_keys):
                    if m == modelo:
                        item.addChild(QTreeWidgetItem([f"Versão {versao}"]))
            self.tree.expandAll()

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.ok_button.setText("Criar")
        self.ok_button.setToolTip("Criar o Modelo/Versão após nova validação dos registos e pastas.")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setToolTip("Fechar sem criar.")
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
        self._start_blink()

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

    def _start_blink(self) -> None:
        self._blink_on = False
        self._blink_timer.start()

    def _blink_tick(self) -> None:
        self._blink_on = not self._blink_on
        for line, base_style in self._blink_base_styles:
            if self._blink_on:
                separator = "" if not base_style or base_style.endswith(";") else ";"
                line.setStyleSheet(
                    f"{base_style}{separator} background-color: #FFF3A6;"
                )
            else:
                line.setStyleSheet(base_style)

    def _stop_blink(self) -> None:
        if self._blink_timer.isActive():
            self._blink_timer.stop()
        for line, base_style in self._blink_base_styles:
            line.setStyleSheet(base_style)

    def _format_inputs(self) -> None:
        for line in (self.ed_ver_obra, self.ed_ver_plano):
            text = line.text().strip()
            if text:
                line.setText(self._norm_two_digits(text))
        self._refresh_status()

    def _refresh_status(self) -> None:
        vv, pp = self.values()
        duplicate = bool(vv and pp and (vv, pp) in self._existing_keys)
        if (vv, pp) in self._streamlit_keys:
            self.warning_label.setText(
                f"O Modelo {vv} / Versão {pp} já existe no Streamlit, mesmo que não tenha pasta."
            )
        elif duplicate:
            self.warning_label.setText(
                f"A versão {vv}/{pp} já existe na BD ou nas pastas do servidor."
            )
        else:
            self.warning_label.clear()
        valid = self.ed_ver_obra.hasAcceptableInput() and self.ed_ver_plano.hasAcceptableInput()
        self.ok_button.setEnabled(valid and not duplicate)

    def _on_accept(self) -> None:
        self._format_inputs()
        vv, pp = self.values()
        if not (self.ed_ver_obra.hasAcceptableInput() and self.ed_ver_plano.hasAcceptableInput()):
            QMessageBox.warning(self, "Novo Modelo/Versão", "Preencha o Modelo e a Versão.")
            return
        if (vv, pp) in self._existing_keys:
            QMessageBox.warning(
                self,
                "Novo Modelo/Versão",
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

    def done(self, result: int) -> None:
        self._stop_blink()
        super().done(result)

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt override)
        self._stop_blink()
        super().closeEvent(event)
