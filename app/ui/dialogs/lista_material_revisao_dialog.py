"""Revisão simples, por peça, das sugestões antes do CUT-RITE."""

from __future__ import annotations

from collections import defaultdict

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.services.lista_material_assistente_service import (
    AssistantDecision,
    AssistantSuggestion,
    MaterialRow,
    WorkbookAudit,
)


SAFE_CONFIDENCE = 0.80
DEFAULT_CUTRITE_COLUMNS = (
    "Descricao", "Material", "Comp", "Larg", "Qt", "Veio", "Orla",
    "Cliente", "Ref_Cliente", "Processo", "Artigo", "Notas", "Esp",
    "Grafico Orlas", "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO",
    "ID", "CNC_1", "CNC_2", "+comp", "+Larg", "Esp.Mat", "Esp.Final",
    "Tipo_Lacagem", "SourceID", "Estado_Assistente",
)
REVIEW_FIRST_COLUMNS = (
    "Descricao", "Material", "Comp", "Larg", "Qt", "Veio", "Artigo", "Notas",
    "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO", "SourceID",
)
ROLE_SUGGESTIONS = int(Qt.ItemDataRole.UserRole)
ROLE_ORIGINAL = ROLE_SUGGESTIONS + 1
ROLE_FIELD = ROLE_SUGGESTIONS + 2
PROTECTED_TECHNICAL_COLUMNS = {"SourceID", "Estado_Assistente"}


class ListaMaterialRevisaoDialog(QDialog):
    """Mostra uma linha por peça e realça apenas as células propostas."""

    def __init__(self, audit: WorkbookAudit, parent=None) -> None:
        super().__init__(parent)
        self.audit = audit
        self._building = True
        self._decision_states = ["pendente"] * len(audit.suggestions)
        self._row_actions: list[QComboBox] = []
        self._suggestion_items: dict[int, QTableWidgetItem] = {}
        self._manual_edits: dict[tuple[int, str], AssistantDecision] = {}
        self._table_row_by_excel_row: dict[int, int] = {}
        self._suggestions_by_excel_row: dict[int, list[int]] = defaultdict(list)
        for index, suggestion in enumerate(audit.suggestions):
            if suggestion.row_number is not None:
                self._suggestions_by_excel_row[int(suggestion.row_number)].append(index)

        excel_columns = tuple(audit.columns) or self._columns_from_rows(audit.rows)
        self._columns = self._review_columns(excel_columns)
        self.setWindowTitle("Assistente Lista Material — rever alterações")
        self.setMinimumSize(1100, 700)
        screen = QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.availableGeometry()
            self.resize(int(geometry.width() * 0.96), int(geometry.height() * 0.92))
        else:
            self.resize(1550, 850)
        self.setWindowState(self.windowState() | Qt.WindowState.WindowMaximized)

        safe_count = sum(
            1
            for suggestion in audit.suggestions
            if (suggestion.suggested or suggestion.allow_blank)
            and not suggestion.blocking
            and suggestion.confidence >= SAFE_CONFIDENCE
        )
        summary = QLabel(
            f"{len(audit.rows)} peças · {len(audit.suggestions)} alterações propostas · "
            f"{len(audit.blocking)} situações para confirmar"
        )
        summary.setStyleSheet("font-size: 16px; font-weight: 650;")
        catalog = QLabel(audit.board_catalog_message)
        catalog.setWordWrap(True)
        catalog.setStyleSheet("color: #5c6570;")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(
            "Pesquisar em qualquer coluna, motivo, material, artigo ou SourceID…"
        )
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._apply_filters)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Todas as peças com propostas", "all")
        self.filter_combo.addItem("Só decisões pendentes", "pending")
        self.filter_combo.addItem("Só situações para confirmar", "blocking")
        self.filter_combo.addItem("Só peças já decididas", "decided")
        self.filter_combo.currentIndexChanged.connect(self._apply_filters)

        self.show_all_check = QCheckBox("Incluir peças sem alterações propostas")
        self.show_all_check.setChecked(False)
        self.show_all_check.toggled.connect(self._apply_filters)

        filter_row = QHBoxLayout()
        filter_row.addWidget(self.search_input, 1)
        filter_row.addWidget(self.filter_combo)
        filter_row.addWidget(self.show_all_check)

        self.table = QTableWidget(len(audit.rows), len(self._columns) + 3)
        self.table.setHorizontalHeaderLabels(
            ["Decisão da peça", "Linha Excel", "Ação Assistente", *self._columns]
        )
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
            | QAbstractItemView.EditTrigger.SelectedClicked
        )
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(27)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self._populate_table()
        self.table.itemChanged.connect(self._on_item_changed)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setMinimumSectionSize(58)
        header.setStretchLastSection(False)
        self._set_column_widths()

        legend = QLabel(
            "<span style='background:#fff2cc;padding:3px 8px'>Amarelo: proposta</span>  "
            "<span style='background:#f4cccc;padding:3px 8px'>Vermelho: preencher/confirmar</span>  "
            "<span style='background:#d9ead3;padding:3px 8px'>Verde: aceite/editado</span>  "
            "<span style='background:#e5e7eb;padding:3px 8px'>Cinzento: manter valor atual</span>  "
            "<span style='background:#cfe2f3;padding:3px 8px'>Azul: edição manual</span>"
        )

        accept_safe = QPushButton(f"Aceitar sugestões seguras ({safe_count})")
        accept_safe.setToolTip(
            "Aceitar propostas preenchidas, não bloqueantes e com confiança de 80% ou mais"
        )
        accept_safe.clicked.connect(self._accept_safe)
        accept_visible = QPushButton("Aceitar propostas visíveis (inclui vazios)")
        accept_visible.setToolTip(
            "Aceitar explicitamente todas as propostas visíveis após os filtros, "
            "incluindo células cujo valor final proposto é vazio"
        )
        accept_visible.clicked.connect(
            lambda: self._set_all(
                "aceitar", visible_only=True, allow_empty=True
            )
        )
        reject_visible = QPushButton("Manter sem alteração as pendentes visíveis")
        reject_visible.setToolTip(
            "Confirmar que as propostas ainda pendentes e visíveis devem manter o valor atual, "
            "incluindo situações vermelhas sem correspondência automática"
        )
        reject_visible.clicked.connect(
            lambda: self._set_all(
                "rejeitar", visible_only=True, pending_only=True
            )
        )
        bulk_row = QHBoxLayout()
        bulk_row.addWidget(accept_safe)
        bulk_row.addWidget(accept_visible)
        bulk_row.addWidget(reject_visible)
        bulk_row.addStretch()

        self.progress_label = QLabel()
        self.progress_label.setStyleSheet("font-weight: 600;")
        self.status_label = QLabel(
            "Uma decisão por peça aplica-se aos campos realçados dessa peça. "
            "Pode editar diretamente qualquer célula operacional ou aceitar explicitamente "
            "um campo vazio como válido; SourceID e Estado são técnicos."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #5c6570;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            "Aplicar alterações selecionadas"
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setToolTip(
            "Aplicar apenas valores aceites/editados e guardar todas as decisões"
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Fechar sem alterar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setToolTip(
            "Não alterar o Excel"
        )
        buttons.accepted.connect(self._validate)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(summary)
        layout.addWidget(catalog)
        layout.addLayout(filter_row)
        layout.addWidget(legend)
        layout.addWidget(self.table, 1)
        layout.addLayout(bulk_row)
        layout.addWidget(self.progress_label)
        layout.addWidget(self.status_label)
        layout.addWidget(buttons)

        self._building = False
        self._refresh_view()

    @staticmethod
    def _columns_from_rows(rows: tuple[MaterialRow, ...]) -> tuple[str, ...]:
        for row in rows:
            if row.values:
                return tuple(row.values)
        return DEFAULT_CUTRITE_COLUMNS

    @staticmethod
    def _review_columns(excel_columns: tuple[str, ...]) -> tuple[str, ...]:
        """Mantém todas as colunas, aproximando contexto e campos alteráveis."""
        first = [name for name in REVIEW_FIRST_COLUMNS if name in excel_columns]
        return tuple(first + [name for name in excel_columns if name not in first])

    @staticmethod
    def _row_value(row: MaterialRow, column: str) -> str:
        if column in row.values:
            return row.values[column]
        fallback = {
            "Descricao": row.description,
            "Material": row.material,
            "Comp": str(row.length or ""),
            "Larg": str(row.width or ""),
            "Qt": str(row.quantity or ""),
            "Artigo": row.article,
            "Notas": row.notes,
            "SourceID": row.source_id,
            **row.edges,
        }
        return fallback.get(column, "")

    def _populate_table(self) -> None:
        column_indexes = {name: index + 3 for index, name in enumerate(self._columns)}
        for table_row, material_row in enumerate(self.audit.rows):
            self._table_row_by_excel_row[material_row.row_number] = table_row
            suggestion_indexes = self._suggestions_by_excel_row.get(
                material_row.row_number, []
            )
            action = QComboBox()
            action.addItem("Pendente", "pendente")
            action.addItem("Aceitar alterações / validar vazio", "aceitar")
            action.addItem("Manter valores atuais da peça", "rejeitar")
            action.addItem("Decisão parcial", "partial")
            partial_item = action.model().item(3)
            if partial_item is not None:
                partial_item.setEnabled(False)
            action.setEnabled(bool(suggestion_indexes))
            action.currentIndexChanged.connect(
                lambda _index, row=table_row: self._on_row_action(row)
            )
            self.table.setCellWidget(table_row, 0, action)
            self._row_actions.append(action)

            line_item = QTableWidgetItem(str(material_row.row_number))
            line_item.setFlags(line_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            line_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(table_row, 1, line_item)
            assistant_action = QTableWidgetItem("")
            assistant_action.setFlags(
                assistant_action.flags() & ~Qt.ItemFlag.ItemIsEditable
            )
            self.table.setItem(table_row, 2, assistant_action)
            for column, name in enumerate(self._columns, start=3):
                item = QTableWidgetItem(self._row_value(material_row, name))
                item.setData(ROLE_ORIGINAL, item.text())
                item.setData(ROLE_FIELD, name)
                if name in PROTECTED_TECHNICAL_COLUMNS:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    item.setToolTip(
                        "Duplo clique para editar manualmente este valor antes de aplicar."
                    )
                self.table.setItem(table_row, column, item)

            by_field: dict[str, list[int]] = defaultdict(list)
            for suggestion_index in suggestion_indexes:
                suggestion = self.audit.suggestions[suggestion_index]
                by_field[suggestion.field].append(suggestion_index)
            for field, indexes in by_field.items():
                column = 2 if field == "__DELETE_ROW__" else column_indexes.get(field)
                if column is None:
                    continue
                suggestion = self.audit.suggestions[indexes[-1]]
                item = self.table.item(table_row, column) or QTableWidgetItem()
                if self.table.item(table_row, column) is None:
                    self.table.setItem(table_row, column, item)
                item.setText(suggestion.suggested)
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
                if field == "__DELETE_ROW__":
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                item.setData(ROLE_SUGGESTIONS, indexes)
                item.setToolTip(self._suggestion_tooltip(indexes))
                for suggestion_index in indexes:
                    self._suggestion_items[suggestion_index] = item

    def _suggestion_tooltip(self, indexes: list[int]) -> str:
        parts = []
        for index in indexes:
            suggestion = self.audit.suggestions[index]
            proposed = suggestion.suggested or "(preencher manualmente)"
            parts.append(
                f"Original: {suggestion.original or '(vazio)'}\n"
                f"Proposta: {proposed}\n"
                f"Confiança: {suggestion.confidence:.0%}\nMotivo: {suggestion.reason}"
            )
        return "\n\n".join(parts)

    def _set_column_widths(self) -> None:
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 78)
        self.table.setColumnWidth(2, 190)
        widths = {
            "Descricao": 210, "Material": 260, "Comp": 80, "Larg": 80,
            "Qt": 65, "Cliente": 150, "Ref_Cliente": 110, "Processo": 145,
            "Artigo": 150, "Notas": 290, "Orla ESQ": 165, "Orla DIR": 165,
            "Orla CIMA": 165, "Orla BAIXO": 165, "SourceID": 115,
            "Estado_Assistente": 130,
        }
        for index, name in enumerate(self._columns, start=3):
            self.table.setColumnWidth(index, widths.get(name, 92))

    def decisions(self) -> list[AssistantDecision]:
        result: list[AssistantDecision] = []
        for index, suggestion in enumerate(self.audit.suggestions):
            action = self._decision_states[index]
            item = self._suggestion_items.get(index)
            value = item.text().strip() if item is not None else suggestion.suggested
            if action == "aceitar" and value != suggestion.suggested:
                action = "editar"
            result.append(AssistantDecision(suggestion, action, value))
        result.extend(self._manual_edits.values())
        return result

    def _on_row_action(self, table_row: int) -> None:
        if self._building:
            return
        material_row = self.audit.rows[table_row]
        indexes = self._suggestions_by_excel_row.get(material_row.row_number, [])
        action = str(self._row_actions[table_row].currentData())
        if action == "partial":
            return
        for index in indexes:
            suggestion = self.audit.suggestions[index]
            item = self._suggestion_items.get(index)
            value = item.text().strip() if item is not None else suggestion.suggested
            if action == "aceitar":
                # A escolha explícita do utilizador valida também um vazio.
                # Os botões automáticos continuam conservadores e não aceitam
                # ambiguidades vazias sem esta confirmação humana.
                self._decision_states[index] = "aceitar"
            elif action == "rejeitar":
                self._decision_states[index] = "rejeitar"
            else:
                self._decision_states[index] = "pendente"
        self._refresh_view()

    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._building:
            return
        indexes = item.data(ROLE_SUGGESTIONS)
        value = item.text().strip()
        if indexes:
            for index in indexes:
                # Uma edição direta é uma decisão explícita, mesmo quando o
                # valor final pretendido é vazio.
                self._decision_states[index] = "editar"
        else:
            field = str(item.data(ROLE_FIELD) or "")
            if not field or field in PROTECTED_TECHNICAL_COLUMNS:
                return
            material_row = self.audit.rows[item.row()]
            original = str(item.data(ROLE_ORIGINAL) or "")
            key = (material_row.row_number, field)
            if value == original:
                self._manual_edits.pop(key, None)
                item.setBackground(QBrush())
                font = item.font()
                font.setBold(False)
                item.setFont(font)
            else:
                suggestion = AssistantSuggestion(
                    source_id=material_row.source_id,
                    row_number=material_row.row_number,
                    field=field,
                    original=original,
                    suggested=value,
                    reason="Valor editado manualmente no Assistente Lista Material.",
                    confidence=1.0,
                    kind="edicao_manual",
                    allow_blank=True,
                )
                self._manual_edits[key] = AssistantDecision(
                    suggestion=suggestion,
                    action="editar",
                    value=value,
                )
                item.setBackground(QBrush(QColor("#cfe2f3")))
                font = item.font()
                font.setBold(True)
                item.setFont(font)
        self._refresh_view()

    def _accept_safe(self) -> None:
        for index, suggestion in enumerate(self.audit.suggestions):
            if (
                (suggestion.suggested or suggestion.allow_blank)
                and not suggestion.blocking
                and suggestion.confidence >= SAFE_CONFIDENCE
            ):
                self._decision_states[index] = "aceitar"
        self.filter_combo.setCurrentIndex(self.filter_combo.findData("pending"))
        self._refresh_view()

    def _set_all(
        self,
        action: str,
        *,
        visible_only: bool = False,
        pending_only: bool = False,
        allow_empty: bool = False,
    ) -> None:
        for index, suggestion in enumerate(self.audit.suggestions):
            table_row = self._table_row_by_excel_row.get(suggestion.row_number or -1)
            if visible_only and (table_row is None or self.table.isRowHidden(table_row)):
                continue
            if pending_only and self._decision_states[index] != "pendente":
                continue
            item = self._suggestion_items.get(index)
            value = item.text().strip() if item is not None else suggestion.suggested
            if (
                action == "aceitar"
                and not allow_empty
                and not value
                and not suggestion.allow_blank
            ):
                continue
            self._decision_states[index] = action
        self._refresh_view()

    def _set_row_combo_summary(self, table_row: int) -> None:
        material_row = self.audit.rows[table_row]
        indexes = self._suggestions_by_excel_row.get(material_row.row_number, [])
        combo = self._row_actions[table_row]
        if not indexes:
            return
        states = [self._decision_states[index] for index in indexes]
        if all(state == "pendente" for state in states):
            summary = "pendente"
        elif all(state in {"aceitar", "editar"} for state in states):
            summary = "aceitar"
        elif all(state == "rejeitar" for state in states):
            summary = "rejeitar"
        else:
            summary = "partial"
        wanted = combo.findData(summary)
        combo.blockSignals(True)
        if wanted >= 0:
            combo.setCurrentIndex(wanted)
        combo.blockSignals(False)
        accepted = sum(state in {"aceitar", "editar"} for state in states)
        rejected = sum(state == "rejeitar" for state in states)
        pending = len(states) - accepted - rejected
        combo.setToolTip(
            f"Nesta peça: {accepted} aceites/editadas, {rejected} rejeitadas, {pending} pendentes"
        )

    def _refresh_item_styles(self) -> None:
        grouped: dict[int, tuple[QTableWidgetItem, list[int]]] = {}
        for index, item in self._suggestion_items.items():
            key = id(item)
            if key not in grouped:
                grouped[key] = (item, [])
            grouped[key][1].append(index)
        for item, indexes in grouped.values():
            states = [self._decision_states[index] for index in indexes]
            if all(state == "rejeitar" for state in states):
                color = QColor("#e5e7eb")
            elif any(state in {"aceitar", "editar"} for state in states):
                color = QColor("#d9ead3")
            elif any(self.audit.suggestions[index].blocking for index in indexes):
                color = QColor("#f4cccc")
            else:
                color = QColor("#fff2cc")
            item.setBackground(QBrush(color))
            font = item.font()
            font.setBold(True)
            item.setFont(font)

    def _refresh_removed_row_styles(self) -> None:
        """Risca as linhas cuja remoção por agrupamento foi aceite (Ctrl+5)."""
        for table_row, material_row in enumerate(self.audit.rows):
            indexes = self._suggestions_by_excel_row.get(
                material_row.row_number, []
            )
            strike = any(
                self.audit.suggestions[index].delete_row
                and self._decision_states[index] in {"aceitar", "editar"}
                for index in indexes
            )
            for column in range(1, self.table.columnCount()):
                item = self.table.item(table_row, column)
                if item is None:
                    continue
                font = item.font()
                font.setStrikeOut(strike)
                item.setFont(font)
            combo = self._row_actions[table_row]
            combo_font = combo.font()
            combo_font.setStrikeOut(strike)
            combo.setFont(combo_font)

    def _apply_filters(self) -> None:
        if self._building:
            return
        search = self.search_input.text().strip().casefold()
        mode = str(self.filter_combo.currentData())
        include_without = self.show_all_check.isChecked()
        for table_row, material_row in enumerate(self.audit.rows):
            indexes = self._suggestions_by_excel_row.get(material_row.row_number, [])
            states = [self._decision_states[index] for index in indexes]
            pending = any(state == "pendente" for state in states)
            blocking = any(
                self.audit.suggestions[index].blocking
                and self._decision_states[index] == "pendente"
                for index in indexes
            )
            decided = bool(states) and not pending
            has_manual = any(
                excel_row == material_row.row_number
                for excel_row, _field in self._manual_edits
            )
            visible = bool(indexes) or has_manual or include_without
            if mode == "pending":
                visible = visible and pending
            elif mode == "blocking":
                visible = visible and blocking
            elif mode == "decided":
                visible = visible and decided
            if visible and search:
                row_text = " ".join(
                    self.table.item(table_row, column).text()
                    for column in range(1, self.table.columnCount())
                    if self.table.item(table_row, column) is not None
                )
                reasons = " ".join(
                    self.audit.suggestions[index].reason for index in indexes
                )
                visible = search in f"{row_text} {reasons}".casefold()
            self.table.setRowHidden(table_row, not visible)

    def _refresh_progress(self) -> None:
        accepted = sum(
            state in {"aceitar", "editar"} for state in self._decision_states
        )
        rejected = sum(state == "rejeitar" for state in self._decision_states)
        pending = len(self._decision_states) - accepted - rejected
        unresolved = sum(
            suggestion.blocking and self._decision_states[index] == "pendente"
            for index, suggestion in enumerate(self.audit.suggestions)
        )
        visible_rows = sum(
            not self.table.isRowHidden(row) for row in range(self.table.rowCount())
        )
        self.progress_label.setText(
            f"Progresso: {accepted} aceites/editadas · {rejected} mantidas sem alteração · "
            f"{pending} pendentes · {unresolved} confirmações obrigatórias · "
            f"{len(self._manual_edits)} edições manuais · {visible_rows} peças visíveis"
        )

    def _refresh_view(self) -> None:
        self._building = True
        try:
            self._refresh_item_styles()
            self._refresh_removed_row_styles()
            for table_row in range(len(self.audit.rows)):
                self._set_row_combo_summary(table_row)
        finally:
            self._building = False
        self._apply_filters()
        self._refresh_progress()

    def _validate(self) -> None:
        decisions = self.decisions()
        if any(item.action == "pendente" for item in decisions):
            self.status_label.setText(
                "Ainda existem propostas pendentes. Use os botões em massa e reveja apenas as situações a vermelho."
            )
            self.filter_combo.setCurrentIndex(self.filter_combo.findData("pending"))
            return
        grouped: dict[str, list[AssistantDecision]] = defaultdict(list)
        for item in decisions:
            if item.suggestion.group_id:
                grouped[item.suggestion.group_id].append(item)
        incomplete_groups = [
            items
            for items in grouped.values()
            if {
                "aplicar" if item.action in {"aceitar", "editar"} else item.action
                for item in items
            }
            not in ({"aplicar"}, {"rejeitar"})
        ]
        if incomplete_groups:
            self.status_label.setText(
                "Um agrupamento deve ser aceite ou rejeitado por completo: Comp, Qt e linhas a remover."
            )
            return
        self.accept()
