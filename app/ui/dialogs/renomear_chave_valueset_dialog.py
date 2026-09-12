"""Mostrar quem usa uma chave ValueSet antes de lhe mudar o código."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.def_valueset_chave_renomeacao_service import OcorrenciasChave
from app.ui.tema import CINZA_ESCURO, TEXTO_AVISO


class RenomearChaveValuesetDialog(QDialog):
    """Confirmação explícita para renomear uma chave ValueSet.

    Renomear uma chave sem mais nada deixava toda a gente que a usava com o
    nome antigo — e sem dar erro nenhum. Este diálogo põe os números à frente
    e obriga a escolher o alcance antes de avançar.
    """

    HEADERS = ["Onde", "Quantas"]

    def __init__(
        self,
        ocorrencias: OcorrenciasChave,
        codigo_novo: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.ocorrencias = ocorrencias
        self.codigo_novo = codigo_novo

        self.setWindowTitle("Renomear chave ValueSet")
        self.setModal(True)
        self.setMinimumWidth(560)

        titulo = QLabel(
            f"Renomear <b>{ocorrencias.codigo}</b> para <b>{codigo_novo}</b>."
        )
        titulo.setWordWrap(True)

        explicacao = QLabel(
            "O código da chave está guardado como texto em vários sítios, sem "
            "ligação entre eles. Quem ficar com o nome antigo <b>não dá erro</b>: "
            "no custeio a lista de materiais dessa chave vem simplesmente vazia."
        )
        explicacao.setWordWrap(True)
        explicacao.setStyleSheet(f"color: {CINZA_ESCURO};")

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        cabecalho = self.table.horizontalHeader()
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        cabecalho.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._preencher()

        self.incluir_orcamentos_check = QCheckBox(
            "Mudar também nos orçamentos já feitos "
            f"({ocorrencias.total_orcamentos} linha(s))"
        )
        self.incluir_orcamentos_check.setChecked(False)
        self.incluir_orcamentos_check.setToolTip(
            "Os orçamentos guardam o que foi vendido, com os preços e as "
            "descrições desse dia. Mudar a chave neles reescreve esse registo. "
            "Normalmente basta corrigir os catálogos."
        )
        self.incluir_orcamentos_check.setEnabled(ocorrencias.total_orcamentos > 0)
        self.incluir_orcamentos_check.stateChanged.connect(
            lambda _=0: self._atualizar_aviso()
        )

        self.aviso_label = QLabel("")
        self.aviso_label.setWordWrap(True)
        self.aviso_label.setStyleSheet(f"color: {TEXTO_AVISO};")

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botao_ok = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        botao_ok.setText("Renomear")
        botao_ok.setToolTip("Mudar o código da chave e de quem a usa.")
        cancelar = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancelar.setToolTip("Sair sem mudar nada.")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.addWidget(titulo)
        layout.addWidget(explicacao)
        layout.addWidget(self.table)
        layout.addWidget(self.incluir_orcamentos_check)
        layout.addWidget(self.aviso_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._atualizar_aviso()

    @property
    def incluir_orcamentos(self) -> bool:
        """Se o utilizador pediu para mexer também nos orçamentos."""
        return self.incluir_orcamentos_check.isChecked()

    def _preencher(self) -> None:
        """Uma linha por sítio, com um separador entre catálogos e orçamentos."""
        linhas: list[tuple[str, str, bool]] = []
        linhas.append(
            (
                f"Catálogos — muda sempre ({self.ocorrencias.total_catalogos})",
                "",
                True,
            )
        )
        for ocorrencia in self.ocorrencias.catalogos:
            linhas.append((f"    {ocorrencia.etiqueta}", str(ocorrencia.total), False))
        linhas.append(
            (
                f"Orçamentos já feitos — só se pedir "
                f"({self.ocorrencias.total_orcamentos})",
                "",
                True,
            )
        )
        for ocorrencia in self.ocorrencias.orcamentos:
            linhas.append((f"    {ocorrencia.etiqueta}", str(ocorrencia.total), False))

        self.table.setRowCount(len(linhas))
        for row, (texto, total, eh_titulo) in enumerate(linhas):
            item_texto = QTableWidgetItem(texto)
            item_total = QTableWidgetItem(total)
            item_total.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            if eh_titulo:
                for item in (item_texto, item_total):
                    fonte = item.font()
                    fonte.setBold(True)
                    item.setFont(fonte)
                    item.setForeground(Qt.GlobalColor.black)
                item_texto.setForeground(Qt.GlobalColor.black)
            self.table.setItem(row, 0, item_texto)
            self.table.setItem(row, 1, item_total)

    def _atualizar_aviso(self) -> None:
        """Dizer, em número de linhas, o que vai acontecer."""
        if self.incluir_orcamentos:
            self.aviso_label.setText(
                f"Vão mudar {self.ocorrencias.total} linha(s), incluindo "
                f"{self.ocorrencias.total_orcamentos} de orçamentos já feitos. "
                "Isso altera o registo do que foi vendido."
            )
            return
        if self.ocorrencias.total_orcamentos:
            self.aviso_label.setText(
                f"Vão mudar {self.ocorrencias.total_catalogos} linha(s) de "
                f"catálogo. As {self.ocorrencias.total_orcamentos} linhas de "
                "orçamentos ficam com o código antigo — servem para consultar, "
                "e é normal ficarem como estão."
            )
            return
        self.aviso_label.setText(
            f"Vão mudar {self.ocorrencias.total_catalogos} linha(s) de catálogo."
        )
