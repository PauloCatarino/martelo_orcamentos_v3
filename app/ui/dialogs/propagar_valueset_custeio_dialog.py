"""Dialog to compare and propagate an item ValueSet line into cost lines."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.domain.numeros import formatar_percentagem
from app.repositories.orcamento_item_custeio_linha_repository import (
    OrcamentoItemCusteioLinhaResumo,
)
from app.utils.formatters import format_currency, format_quantity


class PropagarValuesetCusteioDialog(QDialog):
    """Modal comparison dialog to pick cost lines to update from a ValueSet line."""

    TABLE_HEADERS = [
        "Atualizar?",
        "ID linha",
        "Tipo linha",
        "Código",
        "Descrição",
        "Chave ValueSet",
        "Editado localmente",
        "Material editado localmente",
        "Ref LE atual",
        "Ref LE ValueSet",
        "Descrição atual",
        "Descrição ValueSet",
        "Unidade atual",
        "Unidade ValueSet",
        "PLIQ atual",
        "PLIQ ValueSet",
        "Desp atual",
        "Desp ValueSet",
        "Orla 0.4 atual",
        "Orla 0.4 ValueSet",
        "Orla 1.0 atual",
        "Orla 1.0 ValueSet",
        "Comp MP atual",
        "Comp MP ValueSet",
        "Larg MP atual",
        "Larg MP ValueSet",
        "Esp MP atual",
        "Esp MP ValueSet",
    ]

    def __init__(
        self,
        linhas_custeio: list[OrcamentoItemCusteioLinhaResumo],
        valueset_linha,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.linhas_custeio = linhas_custeio
        self.valueset_linha = valueset_linha
        self.selected_ids: list[int] = []
        self._linhas_by_row: dict[int, OrcamentoItemCusteioLinhaResumo] = {}

        self.setWindowTitle("Atualizar Custeio a partir do ValueSet do Item")
        self.setModal(True)
        self.setMinimumSize(960, 460)

        info = QLabel(
            "Existem linhas de custeio associadas a esta chave ValueSet. "
            "Selecione as linhas a atualizar com os dados do ValueSet do item."
        )
        info.setWordWrap(True)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        self.update_button = QPushButton("Atualizar selecionadas")
        self.update_button.clicked.connect(self._atualizar_selecionadas)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.update_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._preencher()

    def _preencher(self) -> None:
        """Fill the comparison table with the current vs ValueSet values."""
        vs = self.valueset_linha
        self.table.setRowCount(len(self.linhas_custeio))

        for row_index, linha in enumerate(self.linhas_custeio):
            self._linhas_by_row[row_index] = linha

            check_item = QTableWidgetItem()
            check_item.setFlags(check_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            check_item.setCheckState(
                Qt.CheckState.Unchecked
                if linha.material_editado_localmente
                else Qt.CheckState.Checked
            )
            self.table.setItem(row_index, 0, check_item)

            valores = [
                str(linha.id),
                linha.tipo_linha,
                linha.codigo or "",
                linha.descricao or "",
                linha.chave_valueset or "",
                "Sim" if linha.editado_localmente else "Não",
                "Sim" if linha.material_editado_localmente else "Não",
                linha.ref_le or "",
                vs.ref_le or "",
                linha.descricao_no_orcamento or "",
                vs.descricao_no_orcamento or "",
                linha.unidade or "",
                vs.unidade or "",
                format_currency(linha.preco_liquido),
                format_currency(vs.preco_liquido),
                formatar_percentagem(linha.desperdicio_percentagem),
                formatar_percentagem(vs.desperdicio_percentagem),
                linha.coresp_orla_0_4 or "",
                vs.coresp_orla_0_4 or "",
                linha.coresp_orla_1_0 or "",
                vs.coresp_orla_1_0 or "",
                format_quantity(linha.comp_mp),
                format_quantity(vs.comp_mp),
                format_quantity(linha.larg_mp),
                format_quantity(vs.larg_mp),
                format_quantity(linha.esp_mp),
                format_quantity(vs.esp_mp),
            ]
            for offset, value in enumerate(valores):
                self.table.setItem(row_index, offset + 1, QTableWidgetItem(value))

    def _atualizar_selecionadas(self) -> None:
        """Collect the checked line ids and accept."""
        selecionados: list[int] = []
        for row_index, linha in self._linhas_by_row.items():
            item = self.table.item(row_index, 0)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                selecionados.append(linha.id)

        self.selected_ids = selecionados
        self.accept()
