"""Select the global ValueSet model that an explicit publication replaces."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.def_valueset_modelo_service import (
    DefValuesetModeloConteudoResumo,
)
from app.ui import tema
from app.ui.widgets.estilo_tabela_orcamentos import configurar_tabela_orcamentos
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class SubstituirValuesetModeloDialog(QDialog):
    """Show every global target and require one exact row to be selected."""

    HEADERS = ("Código", "Nome", "Descrição", "Estado", "Linhas", "Operações")

    def __init__(
        self,
        origem: DefValuesetModeloConteudoResumo,
        destinos: list[DefValuesetModeloConteudoResumo],
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.origem = origem
        self.destinos = destinos
        self._por_linha: dict[int, DefValuesetModeloConteudoResumo] = {}

        self.setWindowTitle("Publicar Modelo ValueSet para todos")
        self.setModal(True)
        self.setMinimumSize(900, 430)

        modelo = origem.modelo
        origem_label = QLabel(
            f"<b>Origem:</b> {modelo.codigo} — {modelo.nome}<br>"
            f"Conteúdo a publicar: {origem.linhas} linhas e "
            f"{origem.operacoes} operações."
        )
        origem_label.setWordWrap(True)

        instrucao = QLabel(
            "Selecione o modelo global que será substituído. O código global "
            "mantém-se; os restantes dados, materiais, linhas e operações serão "
            "substituídos pela origem."
        )
        instrucao.setWordWrap(True)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        configurar_tabela_orcamentos(self.table, compacta=True)
        ligar_persistencia_larguras(
            self.table, "substituir_valueset_modelo_global"
        )
        self.table.itemSelectionChanged.connect(self._atualizar_supervisor)
        self.table.cellDoubleClicked.connect(lambda _row, _column: self._accept())
        self._preencher()

        self.supervisor_label = QLabel(
            "Selecione exatamente um destino global para ver o que será substituído."
        )
        self.supervisor_label.setObjectName("substituirValuesetModeloSupervisor")
        self.supervisor_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.confirm_button = self.button_box.addButton(
            "Substituir selecionado",
            QDialogButtonBox.ButtonRole.AcceptRole,
        )
        self.confirm_button.setToolTip(
            "Avançar para a confirmação final do modelo global selecionado."
        )
        self.confirm_button.setEnabled(False)
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_button.setText("Cancelar")
        cancel_button.setToolTip("Cancelar sem alterar nenhum modelo.")
        self.confirm_button.clicked.connect(self._accept)
        self.button_box.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(origem_label)
        layout.addWidget(instrucao)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.supervisor_label)
        layout.addWidget(self.button_box)

    @property
    def selected_destino(self) -> DefValuesetModeloConteudoResumo | None:
        row = self.table.currentRow()
        return self._por_linha.get(row)

    def _preencher(self) -> None:
        self.table.setRowCount(len(self.destinos))
        for row, destino in enumerate(self.destinos):
            self._por_linha[row] = destino
            modelo = destino.modelo
            valores = (
                modelo.codigo,
                modelo.nome,
                modelo.descricao or "",
                "Ativo" if modelo.ativo else "Inativo",
                str(destino.linhas),
                str(destino.operacoes),
            )
            for column, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if valor:
                    item.setToolTip(valor)
                self.table.setItem(row, column, item)

    def _atualizar_supervisor(self) -> None:
        destino = self.selected_destino
        if destino is None:
            self.confirm_button.setEnabled(False)
            self.supervisor_label.setText(
                "Selecione exatamente um destino global para ver o que será substituído."
            )
            return

        self.confirm_button.setEnabled(True)
        modelo = destino.modelo
        self.supervisor_label.setStyleSheet("")
        self.supervisor_label.setText(
            f"Destino: {modelo.codigo} — {modelo.nome}. Serão removidas "
            f"{destino.linhas} linhas e {destino.operacoes} operações atuais."
        )

    def _accept(self) -> None:
        if self.selected_destino is None:
            self.supervisor_label.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
            self.supervisor_label.setText(
                "Selecione primeiro o modelo global que pretende substituir."
            )
            return
        self.accept()
