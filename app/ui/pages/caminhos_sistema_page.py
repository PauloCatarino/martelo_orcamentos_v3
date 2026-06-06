"""System paths/settings page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.system_setting_repository import SystemSettingResumo
from app.services.system_setting_service import SystemSettingService


class CaminhosSistemaPage(QWidget):
    """Page for editing system paths and related technical settings."""

    TABLE_HEADERS = [
        "Descri\u00e7\u00e3o / Campo",
        "Valor",
        "Procurar",
    ]
    BROWSE_TYPES = {"pasta", "ficheiro"}

    def __init__(self) -> None:
        super().__init__()

        self._settings_by_row: dict[int, SystemSettingResumo] = {}

        title = QLabel("Caminhos do Sistema")
        title.setObjectName("pageTitle")

        info = QLabel(
            "Configura\u00e7\u00e3o dos caminhos usados pelo Martelo V3 para ficheiros "
            "externos, produ\u00e7\u00e3o, mat\u00e9rias-primas, CNC, IMOS e IA."
        )
        info.setObjectName("pageSubtitle")
        info.setWordWrap(True)

        self.save_button = QPushButton("Guardar Configura\u00e7\u00f5es")
        self.save_button.clicked.connect(self.guardar_configuracoes)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_configuracoes)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.save_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("caminhosSistemaStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(info)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_configuracoes()

    def carregar_configuracoes(self) -> None:
        """Load system settings into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()
        self._settings_by_row = {}

        try:
            with SessionLocal() as session:
                configuracoes = SystemSettingService(session).listar_configuracoes()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os caminhos do sistema.")
            return

        self._preencher_tabela(configuracoes)

        if not configuracoes:
            self.status_label.setText("Sem caminhos do sistema para mostrar.")

    def guardar_configuracoes(self) -> None:
        """Save edited setting values."""
        valores: dict[str, str | None] = {}

        for row_index, setting in self._settings_by_row.items():
            value_item = self.table.item(row_index, 1)
            valores[setting.chave] = value_item.text() if value_item is not None else ""

        try:
            with SessionLocal() as session:
                SystemSettingService(session).guardar_varios(valores)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel guardar os caminhos do sistema.")
            return

        self.status_label.setText("Configuracoes guardadas com sucesso.")
        QMessageBox.information(
            self,
            "Caminhos do Sistema",
            "Configuracoes guardadas com sucesso.",
        )
        self.carregar_configuracoes()

    def _preencher_tabela(self, configuracoes: list[SystemSettingResumo]) -> None:
        """Fill the table with system setting read models."""
        self._settings_by_row = {}
        self.table.setRowCount(len(configuracoes))

        for row_index, setting in enumerate(configuracoes):
            self._settings_by_row[row_index] = setting

            label_item = QTableWidgetItem(setting.descricao or setting.chave)
            label_item.setData(Qt.ItemDataRole.UserRole, setting.chave)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)

            value_item = QTableWidgetItem(setting.valor or "")

            self.table.setItem(row_index, 0, label_item)
            self.table.setItem(row_index, 1, value_item)

            browse_button = QPushButton("Procurar...")
            browse_button.setEnabled(setting.tipo in self.BROWSE_TYPES)
            browse_button.clicked.connect(lambda _checked=False, row=row_index: self._procurar(row))
            self.table.setCellWidget(row_index, 2, browse_button)

    def _procurar(self, row_index: int) -> None:
        """Open a basic file/folder chooser for the selected row."""
        setting = self._settings_by_row.get(row_index)
        if setting is None:
            return

        current_item = self.table.item(row_index, 1)
        current_value = current_item.text() if current_item is not None else ""

        if setting.tipo == "pasta":
            selected = QFileDialog.getExistingDirectory(
                self,
                "Selecionar pasta",
                current_value,
            )
        elif setting.tipo == "ficheiro":
            selected, _ = QFileDialog.getOpenFileName(
                self,
                "Selecionar ficheiro",
                current_value,
            )
        else:
            selected = ""

        if selected:
            self.table.setItem(row_index, 1, QTableWidgetItem(selected))
