"""Dialog to review ValueSet price differences against the material catalog."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.domain.valueset_precos import DivergenciaPreco
from app.utils.formatters import format_currency


class AtualizarPrecosValuesetDialog(QDialog):
    """Modal dialog for choosing which ValueSet prices to update."""

    TABLE_HEADERS = [
        "✓ Atualizar?",
        "Chave",
        "Opção",
        "Ref LE",
        "Preço tabela (guardado)",
        "Preço tabela (atual MP)",
        "Preço líquido novo",
    ]

    HEADER_TOOLTIPS = [
        "Marque as linhas cujo preço deve ser atualizado.",
        "Chave ValueSet da linha.",
        "Código e nome da opção ValueSet.",
        "Referência LE usada para resolver a matéria-prima atual.",
        "Preço tabela guardado atualmente na linha ValueSet.",
        "Preço tabela atual na tabela de Matérias-Primas.",
        "Preço líquido recalculado preservando margem e desconto da linha.",
    ]

    def __init__(
        self,
        divergencias: list[DivergenciaPreco],
        *,
        mostrar_atualizar_modelo_origem: bool = False,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.divergencias = divergencias
        self.selected_divergencias: list[DivergenciaPreco] = []
        self.atualizar_modelo_origem = mostrar_atualizar_modelo_origem
        self._divergencias_by_row: dict[int, DivergenciaPreco] = {}

        self.setWindowTitle("Atualizar preços ValueSet")
        self.setModal(True)
        self.setMinimumSize(940, 420)

        info = QLabel(
            "Foram encontrados preços ValueSet diferentes da tabela de Matérias-Primas. "
            "Selecione as linhas a atualizar."
        )
        info.setWordWrap(True)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        for index, tooltip in enumerate(self.HEADER_TOOLTIPS):
            item = self.table.horizontalHeaderItem(index)
            if item is not None:
                item.setToolTip(tooltip)

        self.atualizar_modelo_origem_input = QCheckBox(
            "Atualizar também o modelo de origem"
        )
        self.atualizar_modelo_origem_input.setChecked(True)
        self.atualizar_modelo_origem_input.setVisible(mostrar_atualizar_modelo_origem)

        self.update_button = QPushButton("Atualizar selecionadas")
        self.update_button.clicked.connect(self._atualizar_selecionadas)
        self.keep_button = QPushButton("Manter tudo")
        self.keep_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.atualizar_modelo_origem_input)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.update_button)
        buttons_layout.addWidget(self.keep_button)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._preencher()

    def _preencher(self) -> None:
        """Fill the table with detected price differences."""
        self.table.setRowCount(len(self.divergencias))

        for row_index, divergencia in enumerate(self.divergencias):
            self._divergencias_by_row[row_index] = divergencia

            check_item = QTableWidgetItem()
            check_item.setFlags(check_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            check_item.setCheckState(Qt.CheckState.Checked)
            self.table.setItem(row_index, 0, check_item)

            opcao = divergencia.codigo_opcao or ""
            if divergencia.nome_opcao:
                opcao = f"{opcao} - {divergencia.nome_opcao}" if opcao else divergencia.nome_opcao

            valores = [
                divergencia.chave,
                opcao,
                divergencia.ref_le or "",
                format_currency(divergencia.preco_tabela_antigo),
                format_currency(divergencia.preco_tabela_atual),
                format_currency(divergencia.preco_liquido_novo),
            ]
            for offset, value in enumerate(valores):
                self.table.setItem(row_index, offset + 1, QTableWidgetItem(value))

    def _atualizar_selecionadas(self) -> None:
        """Collect checked differences and accept the dialog."""
        selecionadas: list[DivergenciaPreco] = []
        for row_index, divergencia in self._divergencias_by_row.items():
            item = self.table.item(row_index, 0)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                selecionadas.append(divergencia)

        self.selected_divergencias = selecionadas
        self.atualizar_modelo_origem = (
            self.atualizar_modelo_origem_input.isVisible()
            and self.atualizar_modelo_origem_input.isChecked()
        )
        self.accept()
