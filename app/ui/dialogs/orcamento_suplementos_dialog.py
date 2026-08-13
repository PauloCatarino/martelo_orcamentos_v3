"""Dialog for global non-stock board supplements in one budget version."""

from __future__ import annotations

from decimal import Decimal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from app.services.orcamento_suplemento_service import (
    GuardarSuplementoPlacaData,
    SuplementoPlacaResumo,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_quantity


class OrcamentoSuplementosDialog(QDialog):
    """Select one supplement per distinct board reference in the budget."""

    HEADERS = (
        "Aplicar",
        "Ref. placa",
        "Descrição",
        "Esp.",
        "Itens",
        "Qt",
        "Fonte",
        "Valor base",
        "Valor local",
        "Notas para o cliente",
    )

    def __init__(
        self,
        suplementos: list[SuplementoPlacaResumo],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._suplementos = suplementos
        self._checks: list[QCheckBox] = []
        self._valores: list[QDoubleSpinBox] = []
        self._notas: list[QLineEdit] = []
        self._quantidades: list[QSpinBox] = []

        self.setWindowTitle("Suplementos de placas não stock")
        self.resize(1040, 620)

        info = QLabel(
            "Selecione as referências que a fábrica cobra como encomenda especial. "
            "Cada referência é cobrada uma única vez em todo o orçamento, mesmo "
            "quando aparece em vários items."
        )
        info.setWordWrap(True)

        regra = QLabel(
            "O valor base vem da matéria-prima PLC0120. O valor local pode ser "
            "alterado apenas para este orçamento e é o preço unitário final, "
            "sem margens adicionais. Qt passa para a linha do orçamento."
        )
        regra.setWordWrap(True)

        self.table = QTableWidget(len(suplementos), len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        larguras_iniciais = (55, 75, 180, 45, 45, 70, 60, 75, 110, 230)
        for coluna, largura in enumerate(larguras_iniciais):
            self.table.setColumnWidth(coluna, largura)
        ligar_persistencia_larguras(
            self.table,
            "dialog_orcamento_suplementos",
            guardar_ordem=True,
        )
        self._preencher()

        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        botoes.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        botoes.button(QDialogButtonBox.StandardButton.Save).setToolTip(
            "Guardar os suplementos desta versão do orçamento"
        )
        botoes.button(QDialogButtonBox.StandardButton.Cancel).setToolTip(
            "Fechar sem alterar os suplementos"
        )
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)

        estado = QLabel(
            f"Referências de placas encontradas: {len(suplementos)}"
            if suplementos
            else "Não foram encontradas placas nas linhas de custeio."
        )

        layout = QVBoxLayout(self)
        layout.addWidget(info)
        layout.addWidget(regra)
        layout.addWidget(self.table, 1)
        layout.addWidget(estado)
        layout.addWidget(botoes)

    def _preencher(self) -> None:
        for row, suplemento in enumerate(self._suplementos):
            check = QCheckBox()
            check.setChecked(suplemento.ativo)
            check.setToolTip(
                "Aplicar uma única cobrança a esta referência no orçamento"
            )
            check_box = QWidget()
            check_layout = QHBoxLayout(check_box)
            check_layout.setContentsMargins(0, 0, 0, 0)
            check_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            check_layout.addWidget(check)
            self.table.setCellWidget(row, 0, check_box)

            values = (
                suplemento.ref_le,
                suplemento.descricao,
                format_quantity(suplemento.esp),
                str(suplemento.numero_itens),
            )
            for column, value in enumerate(values, start=1):
                self.table.setItem(row, column, QTableWidgetItem(value))

            quantidade = QSpinBox()
            quantidade.setRange(1, 9999)
            quantidade.setValue(int(suplemento.quantidade))
            quantidade.setToolTip(
                "Quantidade cobrada desta referência; passa para a linha do orçamento"
            )
            self.table.setCellWidget(row, 5, quantidade)
            self.table.setItem(
                row, 6, QTableWidgetItem(suplemento.suplemento_ref_le)
            )
            self.table.setItem(
                row, 7, QTableWidgetItem(format_currency(suplemento.valor_base))
            )

            valor = QDoubleSpinBox()
            valor.setDecimals(2)
            valor.setRange(0, 999999.99)
            valor.setSuffix(" €")
            valor.setValue(float(suplemento.valor_local))
            valor.setToolTip(
                "Preço unitário final do suplemento nesta versão, sem margens"
            )
            self.table.setCellWidget(row, 8, valor)
            nota = QLineEdit(suplemento.nota_cliente)
            nota.setPlaceholderText(
                "Ex.: Material fora de stock; encomenda especial à fábrica."
            )
            nota.setToolTip(
                "Nota apresentada na linha do suplemento e nos relatórios do cliente"
            )
            self.table.setCellWidget(row, 9, nota)
            self._checks.append(check)
            self._valores.append(valor)
            self._notas.append(nota)
            self._quantidades.append(quantidade)

    def dados(self) -> list[GuardarSuplementoPlacaData]:
        """Return all choices, including disabled rows, for deterministic saving."""
        return [
            GuardarSuplementoPlacaData(
                ref_le=suplemento.ref_le,
                descricao=suplemento.descricao,
                esp=suplemento.esp,
                ativo=self._checks[index].isChecked(),
                valor_local=Decimal(str(self._valores[index].value())),
                nota_cliente=self._notas[index].text().strip(),
                quantidade=Decimal(self._quantidades[index].value()),
            )
            for index, suplemento in enumerate(self._suplementos)
        ]
