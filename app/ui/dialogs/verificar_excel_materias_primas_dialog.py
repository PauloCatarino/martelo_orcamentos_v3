"""Dialog showing what is wrong in the raw-materials Excel, before importing."""

from __future__ import annotations

from PySide6.QtGui import QColor, QGuiApplication
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

from app.domain.materias_primas_validacao import (
    AVISO,
    CRITICO,
    INFO,
    AvisoExcel,
    RelatorioExcel,
    resumir,
)
from app.ui import tema
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras

# Background / text colour per severity, reusing the badge palette of the app.
CORES_SEVERIDADE = {
    CRITICO: (tema.VERMELHO_SUAVE, tema.VERMELHO_ESCURO),
    AVISO: (tema.OCRE_SUAVE, tema.OCRE_ESCURO),
    INFO: (tema.AZUL_SUAVE, tema.AZUL_ESCURO),
}


class VerificarExcelMateriasPrimasDialog(QDialog):
    """Read-only report of the raw-materials Excel. Never writes anything."""

    TABLE_HEADERS = [
        "Gravidade",
        "Linha",
        "Ref LE",
        "Descrição",
        "Problema",
        "O que fazer",
    ]

    HEADER_TOOLTIPS = [
        "CRÍTICO impede ou estraga a importação; AVISO merece revisão; "
        "INFO é só para o utilizador saber.",
        "Número da linha no ficheiro Excel.",
        "Referência LE do material.",
        "Descrição do material no orçamento.",
        "O que foi detetado.",
        "Sugestão de correção.",
    ]

    def __init__(
        self,
        relatorio: RelatorioExcel,
        caminho_excel: str | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.relatorio = relatorio

        self.setWindowTitle("Verificar Excel de matérias-primas")
        self.setModal(True)
        self.setMinimumSize(1040, 520)

        self.resumo_label = QLabel(resumir(relatorio))
        self.resumo_label.setWordWrap(True)
        self.resumo_label.setStyleSheet("font-weight: bold;")

        caminho_texto = (
            f"Ficheiro: {caminho_excel}" if caminho_excel else "Ficheiro configurado."
        )
        self.caminho_label = QLabel(
            f"{caminho_texto}\nEsta verificação não grava nada — só lê o Excel e "
            "mostra o que precisa de atenção."
        )
        self.caminho_label.setWordWrap(True)

        self.filtro_criticos = self._criar_filtro(
            f"Críticos ({len(relatorio.criticos)})",
            "Problemas que impedem ou estragam a importação.",
        )
        self.filtro_avisos = self._criar_filtro(
            f"Avisos ({len(relatorio.alertas)})",
            "Situações a rever, como preços antigos ou espessuras que não batem certo.",
        )
        self.filtro_informativos = self._criar_filtro(
            f"Informativos ({len(relatorio.informativos)})",
            "Mudanças detetadas, como preços que subiram ou desceram desde a última importação.",
            marcado=False,
        )

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        cabecalho = self.table.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        cabecalho.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        ligar_persistencia_larguras(self.table, "dialog_verificar_excel_materias_primas")
        for indice, tooltip in enumerate(self.HEADER_TOOLTIPS):
            item = self.table.horizontalHeaderItem(indice)
            if item is not None:
                item.setToolTip(tooltip)

        self.copiar_button = QPushButton("Copiar lista")
        self.copiar_button.setToolTip(
            "Copiar os avisos visíveis para colar no Excel ou num email."
        )
        self.copiar_button.clicked.connect(self._copiar_lista)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.setToolTip("Fechar sem importar.")
        self.fechar_button.clicked.connect(self.accept)

        # Linha do supervisor: acompanha o utilizador, por baixo dos botões.
        self.status_label = QLabel("")
        self.status_label.setObjectName("verificarExcelStatus")

        filtros_layout = QHBoxLayout()
        filtros_layout.addWidget(QLabel("Mostrar:"))
        filtros_layout.addWidget(self.filtro_criticos)
        filtros_layout.addWidget(self.filtro_avisos)
        filtros_layout.addWidget(self.filtro_informativos)
        filtros_layout.addStretch()

        botoes_layout = QHBoxLayout()
        botoes_layout.addStretch()
        botoes_layout.addWidget(self.copiar_button)
        botoes_layout.addWidget(self.fechar_button)

        layout = QVBoxLayout()
        layout.addWidget(self.resumo_label)
        layout.addWidget(self.caminho_label)
        layout.addLayout(filtros_layout)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(botoes_layout)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        self._preencher()

    def _criar_filtro(self, texto: str, tooltip: str, marcado: bool = True) -> QCheckBox:
        """Create one severity filter checkbox."""
        caixa = QCheckBox(texto)
        caixa.setChecked(marcado)
        caixa.setToolTip(tooltip)
        caixa.stateChanged.connect(self._preencher)
        return caixa

    def severidades_visiveis(self) -> set[str]:
        """Severities currently selected in the filters."""
        visiveis = set()
        if self.filtro_criticos.isChecked():
            visiveis.add(CRITICO)
        if self.filtro_avisos.isChecked():
            visiveis.add(AVISO)
        if self.filtro_informativos.isChecked():
            visiveis.add(INFO)
        return visiveis

    def avisos_visiveis(self) -> list[AvisoExcel]:
        """Findings matching the current filters, worst first."""
        visiveis = self.severidades_visiveis()
        ordem = {CRITICO: 0, AVISO: 1, INFO: 2}
        avisos = [a for a in self.relatorio.avisos if a.severidade in visiveis]
        return sorted(avisos, key=lambda a: (ordem.get(a.severidade, 9), a.linha or 0))

    def _preencher(self) -> None:
        """Fill the table with the findings that pass the filters."""
        avisos = self.avisos_visiveis()
        self.table.setRowCount(len(avisos))

        for linha, aviso in enumerate(avisos):
            valores = [
                aviso.severidade,
                str(aviso.linha) if aviso.linha else "",
                aviso.ref_le or "",
                aviso.descricao or "",
                aviso.mensagem,
                aviso.detalhe or "",
            ]
            fundo, texto = CORES_SEVERIDADE.get(aviso.severidade, (None, None))

            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if coluna == 0 and fundo is not None:
                    item.setBackground(QColor(fundo))
                    item.setForeground(QColor(texto))
                self.table.setItem(linha, coluna, item)

        self.table.resizeColumnsToContents()

        if not avisos:
            self.status_label.setText(
                "Nada a mostrar com estes filtros."
                if self.relatorio.avisos
                else "Ficheiro sem problemas — pode importar."
            )
        elif self.relatorio.criticos:
            self.status_label.setText(
                f"{len(self.relatorio.criticos)} problemas críticos: corrija-os no "
                "Excel antes de importar."
            )
        else:
            self.status_label.setText(
                "Sem problemas críticos — a importação pode avançar."
            )

    def texto_para_copiar(self) -> str:
        """Findings as tab-separated text, ready to paste into Excel."""
        linhas = ["\t".join(self.TABLE_HEADERS)]
        for aviso in self.avisos_visiveis():
            linhas.append(
                "\t".join(
                    (
                        aviso.severidade,
                        str(aviso.linha) if aviso.linha else "",
                        aviso.ref_le or "",
                        aviso.descricao or "",
                        aviso.mensagem,
                        aviso.detalhe or "",
                    )
                )
            )
        return "\n".join(linhas)

    def _copiar_lista(self) -> None:
        """Copy the visible findings to the clipboard."""
        area = QGuiApplication.clipboard()
        if area is None:
            return

        area.setText(self.texto_para_copiar())
        self.status_label.setText("Lista copiada — pode colar no Excel ou num email.")
