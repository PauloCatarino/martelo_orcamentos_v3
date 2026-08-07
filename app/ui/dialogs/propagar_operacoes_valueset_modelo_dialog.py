"""Explicit destination selection for ValueSet model operation propagation."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.def_valueset_operacao_propagacao_service import (
    ContextoPropagacaoOperacoesValueset,
    DestinoOperacoesValueset,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class PropagarOperacoesValuesetModeloDialog(QDialog):
    """Show all matches, permissions and exact changes before confirmation."""

    TABLE_HEADERS = [
        "Selecionar",
        "Âmbito",
        "Proprietário",
        "Modelo",
        "Nome do modelo",
        "Opção",
        "Ref LE",
        "Estado modelo",
        "Estado linha",
        "Substituir",
        "Adicionar",
        "Desativar",
        "Alterações previstas",
    ]

    def __init__(
        self,
        contexto: ContextoPropagacaoOperacoesValueset,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.contexto = contexto
        self.selected_ids: list[int] = []
        self._destinos_by_row: dict[int, DestinoOperacoesValueset] = {}
        self._a_preencher = False

        self.setWindowTitle("Propagar operações da linha ValueSet")
        self.setModal(True)
        self.setMinimumSize(1180, 650)

        info = QLabel(
            f"Origem: {contexto.origem_modelo} / {contexto.origem_opcao} — "
            f"{contexto.origem_chave} — Ref LE {contexto.origem_ref_le} — "
            f"{contexto.origem_operacoes} operação(ões).\n"
            "Só são apresentados destinos com a mesma chave ValueSet e a mesma Ref LE. "
            "Marque exatamente as linhas que pretende alterar."
        )
        info.setWordWrap(True)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        self.table.itemChanged.connect(self._atualizar_previsualizacao)
        ligar_persistencia_larguras(
            self.table, "dialog_propagar_operacoes_valueset_modelo"
        )

        preview_label = QLabel("Pré-visualização dos destinos selecionados:")
        self.preview = QPlainTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setMaximumHeight(170)

        self.apply_button = QPushButton("Aplicar aos destinos selecionados")
        self.apply_button.setToolTip(
            "Confirmar e substituir as operações apenas nas linhas marcadas."
        )
        self.apply_button.clicked.connect(self._confirmar)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.setToolTip("Fechar sem alterar qualquer modelo ValueSet.")
        self.cancel_button.clicked.connect(self.reject)

        self.status_label = QLabel("")
        self.status_label.setObjectName("propagarOperacoesValuesetModeloStatus")

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self.apply_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(preview_label)
        layout.addWidget(self.preview)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)
        self.setLayout(layout)

        self._preencher()

    def _preencher(self) -> None:
        """Fill the table without preselecting any destination."""
        self._a_preencher = True
        self.table.setRowCount(len(self.contexto.destinos))
        for row, destino in enumerate(self.contexto.destinos):
            self._destinos_by_row[row] = destino
            check = QTableWidgetItem()
            flags = check.flags() | Qt.ItemFlag.ItemIsUserCheckable
            if not destino.permitido:
                flags &= ~Qt.ItemFlag.ItemIsEnabled
                check.setToolTip(destino.motivo_bloqueio or "Sem permissão.")
            check.setFlags(flags)
            check.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(row, 0, check)

            alteracoes = "; ".join(
                alteracao.descricao for alteracao in destino.alteracoes
            ) or "Sem alterações"
            values = [
                destino.ambito,
                destino.proprietario,
                destino.modelo_codigo,
                destino.modelo_nome,
                destino.nome_opcao or destino.codigo_opcao or f"#{destino.linha_id}",
                destino.ref_le,
                "Ativo" if destino.modelo_ativo else "Inativo",
                "Ativa" if destino.linha_ativa else "Inativa",
                str(destino.substituidas),
                str(destino.adicionadas),
                str(destino.desativadas),
                alteracoes,
            ]
            for column, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setToolTip(
                    destino.motivo_bloqueio
                    if not destino.permitido
                    else (value if column == len(self.TABLE_HEADERS) - 1 else "")
                )
                if not destino.permitido:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(row, column, item)

        self._a_preencher = False
        self.table.resizeColumnsToContents()
        self._atualizar_previsualizacao()

    def _ids_marcados(self) -> list[int]:
        ids: list[int] = []
        for row, destino in self._destinos_by_row.items():
            check = self.table.item(row, 0)
            if (
                destino.permitido
                and check is not None
                and check.checkState() == Qt.CheckState.Checked
            ):
                ids.append(destino.linha_id)
        return ids

    def _atualizar_previsualizacao(self, _item=None) -> None:
        """Describe replacement/add/deactivation for the current selection."""
        if self._a_preencher:
            return
        ids = set(self._ids_marcados())
        selecionados = [d for d in self.contexto.destinos if d.linha_id in ids]
        self.preview.setPlainText(self._texto_previsualizacao(selecionados))

    @staticmethod
    def _texto_previsualizacao(
        destinos: list[DestinoOperacoesValueset],
    ) -> str:
        if not destinos:
            return "Nenhum destino selecionado."

        linhas: list[str] = []
        for destino in destinos:
            linhas.append(
                f"{destino.modelo_codigo} / "
                f"{destino.nome_opcao or destino.codigo_opcao or destino.linha_id}: "
                f"{destino.substituidas} substituir, {destino.adicionadas} adicionar, "
                f"{destino.desativadas} desativar."
            )
            linhas.extend(f"  • {alteracao.descricao}" for alteracao in destino.alteracoes)
        return "\n".join(linhas)

    def _confirmar(self) -> None:
        """Ask final confirmation for exactly the checked destinations."""
        ids = self._ids_marcados()
        if not ids:
            self.status_label.setText("Selecione pelo menos um destino permitido.")
            return

        ids_set = set(ids)
        destinos = [d for d in self.contexto.destinos if d.linha_id in ids_set]
        resumo = self._texto_previsualizacao(destinos)
        confirm = QMessageBox.question(
            self,
            "Confirmar propagação de operações",
            "As operações serão alteradas apenas nos destinos abaixo:\n\n"
            + resumo
            + "\n\nConfirmar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            self.status_label.setText("Confirmação cancelada; nenhuma alteração foi feita.")
            return

        self.selected_ids = ids
        self.accept()
