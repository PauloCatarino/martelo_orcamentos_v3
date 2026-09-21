"""Grelha tipo Excel da LISTAGEM_CUT_RITE («Rever / editar a listagem»).

Pedido do Paulo ao testar a obra lowcost 1568 (21-09-2026): filtros nas
colunas como no Excel, copiar/colar linhas antes ou depois, eliminar linhas,
limpar conteúdo — deixar o quadro pronto para o Excel mudar o mínimo.

Cores: amarelo = proposta do Martelo; vermelho = confirmar; azul = editado à
mão; verde = linha nova; cinzento riscado = linha a remover.
"""
from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QPoint, QSortFilterProxyModel, Qt
from PySide6.QtGui import QAction, QBrush, QColor, QFont, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QDialog, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMenu, QPushButton, QTableView, QVBoxLayout,
    QWidgetAction, QWidget,
)

from app.services.lista_material_grelha_service import GrelhaListagem

PRIMEIRAS = ("Descricao", "Material", "Comp", "Larg", "Qt", "Veio", "Artigo", "Notas",
             "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO")
CORES = {
    "proposta": QColor("#fff2cc"), "confirmar": QColor("#f4cccc"), "editada": QColor("#cfe2f3"),
    "nova": QColor("#d9ead3"), "removida": QColor("#e5e7eb"),
}
VAZIO = "(Vazias)"


class GrelhaModel(QAbstractTableModel):
    FIXAS = ("Linha", "Estado")

    def __init__(self, grelha: GrelhaListagem, columns, parent=None):
        super().__init__(parent)
        self.grelha = grelha
        self.columns = list(columns)
        self.filtered: set[int] = set()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.grelha.rows)

    def columnCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.FIXAS) + len(self.columns)

    def column_name(self, col: int) -> str:
        return self.FIXAS[col] if col < len(self.FIXAS) else self.columns[col - len(self.FIXAS)]

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.column_name(section) + (" ▼" if section in self.filtered else "")
        return None

    def text(self, row: int, col: int) -> str:
        line = self.grelha.rows[row]
        if col == 0:
            return str(line.original_row) if line.original_row else "nova"
        if col == 1:
            return self.grelha.row_state(row)
        return line.values.get(self.column_name(col), "")

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            return self.text(row, col)
        line = self.grelha.rows[row]
        name = self.column_name(col)
        state = self.grelha.cell_state(row, name) if col >= len(self.FIXAS) else (
            "removida" if line.removed else "nova" if line.is_new else "")
        if role == Qt.ItemDataRole.BackgroundRole and state in CORES:
            return QBrush(CORES[state])
        if role == Qt.ItemDataRole.ForegroundRole and state:
            return QBrush(QColor("#1f2328"))
        if role == Qt.ItemDataRole.FontRole and line.removed:
            font = QFont()
            font.setStrikeOut(True)
            return font
        if role == Qt.ItemDataRole.ToolTipRole and col >= len(self.FIXAS):
            proposal = line.proposals.get(name)
            parts = []
            if line.original_row and line.values.get(name) != line.original.get(name):
                parts.append(f"Valor atual no Excel: «{line.original.get(name, '')}»")
            if proposal is not None:
                parts.append(f"Proposta: «{proposal.suggested}» — {proposal.reason}")
            if line.removed and line.delete_proposal is not None:
                parts.append(f"Linha a remover: {line.delete_proposal.reason}")
            if not self.grelha.editable(name):
                parts.append("Coluna do Excel (fórmula ou técnica): não se edita aqui.")
            return "\n".join(parts) or None
        return None

    def flags(self, index):
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        name = self.column_name(index.column())
        if index.column() >= len(self.FIXAS) and self.grelha.editable(name) \
                and not self.grelha.rows[index.row()].removed:
            base |= Qt.ItemFlag.ItemIsEditable
        return base

    def setData(self, index, value, role=Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.EditRole or index.column() < len(self.FIXAS):
            return False
        if self.grelha.set_value(index.row(), self.column_name(index.column()), str(value)):
            self.dataChanged.emit(self.index(index.row(), 0), self.index(index.row(), self.columnCount() - 1))
            return True
        return False

    def refresh(self):
        self.beginResetModel()
        self.endResetModel()


class FiltroModel(QSortFilterProxyModel):
    """Filtro por valores em cada coluna, como o filtro automático do Excel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.allowed: dict[int, set[str]] = {}
        self.only_changes = False

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if self.only_changes and not model.grelha.has_changes(source_row):
            return False
        for col, values in self.allowed.items():
            text = model.text(source_row, col) or VAZIO
            if text not in values:
                return False
        return True

    def refilter(self, change=None):
        """Voltar a filtrar (Qt 6.10+: begin/endFilterChange; antes: invalidateFilter)."""
        if hasattr(self, "beginFilterChange"):
            self.beginFilterChange()
            if change:
                change()
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)
        else:
            if change:
                change()
            self.invalidateFilter()

    def set_filter(self, col: int, values: set[str] | None):
        def change():
            if values is None:
                self.allowed.pop(col, None)
            else:
                self.allowed[col] = values
        self.refilter(change)


class GrelhaListagemDialog(QDialog):
    def __init__(self, grelha: GrelhaListagem, parent=None, *, titulo="Rever / editar a listagem"):
        super().__init__(parent)
        self.grelha = grelha
        self.setWindowTitle(f"LISTAGEM_CUT_RITE — {titulo}")
        self.setWindowFlag(Qt.WindowType.WindowMaximizeButtonHint, True)
        screen = QApplication.primaryScreen()
        if screen is not None:
            geometry = screen.availableGeometry()
            self.resize(int(geometry.width() * .96), int(geometry.height() * .9))
        columns = [c for c in PRIMEIRAS if c in grelha.columns] + [
            c for c in grelha.columns if c not in PRIMEIRAS]
        self.model = GrelhaModel(grelha, columns, self)
        self.proxy = FiltroModel(self)
        self.proxy.setSourceModel(self.model)

        layout = QVBoxLayout(self)
        legend = QLabel(
            "<span style='background:#fff2cc;padding:2px 6px'>Proposta do Martelo</span> "
            "<span style='background:#f4cccc;padding:2px 6px'>Confirmar</span> "
            "<span style='background:#cfe2f3;padding:2px 6px'>Editado à mão</span> "
            "<span style='background:#d9ead3;padding:2px 6px'>Linha nova</span> "
            "<span style='background:#e5e7eb;padding:2px 6px'>A remover</span> — "
            "clique no cabeçalho de uma coluna para filtrar; botão direito para copiar, colar, "
            "eliminar ou limpar. Duplo clique edita a célula.")
        legend.setWordWrap(True)
        layout.addWidget(legend)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                                  | QAbstractItemView.EditTrigger.EditKeyPressed
                                  | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().setDefaultSectionSize(24)
        header = self.view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setSectionsClickable(True)
        header.sectionClicked.connect(self._filter_menu)
        header.setToolTip("Clique para filtrar esta coluna, como no Excel.")
        for col in range(self.model.columnCount()):
            name = self.model.column_name(col)
            self.view.setColumnWidth(col, 60 if col == 0 else 90 if col == 1 else
                                     260 if name in ("Material", "Notas") else
                                     170 if name.startswith("Orla") or name == "Descricao" else 80)
        self.view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.view.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.view, 1)

        self.actions = {}
        tools = QHBoxLayout()
        for key, text, shortcut, slot, tip in (
            ("copy", "Copiar linhas", "Ctrl+C", self.copy_rows, "Copiar as linhas selecionadas (também para o Excel)."),
            ("paste_before", "Colar antes", "Ctrl+Shift+V", lambda: self.paste(after=False),
             "Inserir as linhas copiadas antes da linha selecionada."),
            ("paste_after", "Colar depois", "Ctrl+V", lambda: self.paste(after=True),
             "Inserir as linhas copiadas depois da linha selecionada."),
            ("delete", "Eliminar linhas", "Ctrl+-", self.delete_rows,
             "Eliminar as linhas selecionadas (as do Excel ficam riscadas até aplicar)."),
            ("clear", "Limpar conteúdo", "Delete", self.clear_cells,
             "Apagar o conteúdo das células selecionadas (só colunas editáveis)."),
            ("restore", "Repor original", "Ctrl+R", self.restore_rows,
             "Voltar a linha ao que está no Excel (desfaz propostas, edições e remoção)."),
            ("undo", "Anular", "Ctrl+Z", self.undo, "Desfazer a última operação (colar, eliminar, limpar, editar…)."),
            ("redo", "Refazer", "Ctrl+Y", self.redo, "Refazer a operação anulada."),
        ):
            action = QAction(text, self)
            action.setShortcut(QKeySequence(shortcut))
            action.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
            action.setToolTip(tip)
            action.triggered.connect(slot)
            self.view.addAction(action)
            self.actions[key] = action
            button = QPushButton(f"{text} ({shortcut})")
            button.setToolTip(tip)
            button.clicked.connect(slot)
            tools.addWidget(button)
        self.only_changes = QCheckBox("Só linhas com propostas/alterações")
        self.only_changes.setToolTip("Esconder as linhas que ficam como estão no Excel.")
        self.only_changes.toggled.connect(self._toggle_only_changes)
        tools.addWidget(self.only_changes)
        clear_filters = QPushButton("Limpar filtros")
        clear_filters.setToolTip("Mostrar outra vez todas as linhas.")
        clear_filters.clicked.connect(self._clear_filters)
        tools.addWidget(clear_filters)
        tools.addStretch()
        layout.addLayout(tools)

        self.summary = QLabel()
        layout.addWidget(self.summary)
        buttons = QHBoxLayout()
        buttons.addStretch()
        apply_button = QPushButton("Aplicar no Excel")
        apply_button.setToolTip("Levar ao Excel só o que mudou: células, linhas eliminadas e linhas novas.")
        apply_button.clicked.connect(self.accept)
        cancel = QPushButton("Fechar sem alterar")
        cancel.setToolTip("Não alterar o Excel.")
        cancel.clicked.connect(self.reject)
        buttons.addWidget(apply_button)
        buttons.addWidget(cancel)
        layout.addLayout(buttons)
        self.model.dataChanged.connect(self._update_summary)
        self.model.modelReset.connect(self._update_summary)
        self._update_summary()

    # ---- seleção -----------------------------------------------------------

    def selected_rows(self) -> list[int]:
        rows = {self.proxy.mapToSource(i).row() for i in self.view.selectionModel().selectedIndexes()}
        current = self.view.currentIndex()
        if not rows and current.isValid():
            rows = {self.proxy.mapToSource(current).row()}
        return sorted(rows)

    def selected_cells(self) -> list[tuple[int, str]]:
        cells = []
        for index in self.view.selectionModel().selectedIndexes():
            source = self.proxy.mapToSource(index)
            if source.column() >= len(GrelhaModel.FIXAS):
                cells.append((source.row(), self.model.column_name(source.column())))
        return cells

    # ---- operações ---------------------------------------------------------

    def copy_rows(self):
        rows = self.selected_rows()
        if not rows:
            return
        copied = self.grelha.copy_rows(rows)
        columns = self.model.columns
        text = "\n".join("\t".join(values.get(c, "") for c in columns) for values in copied)
        QApplication.clipboard().setText(text)
        self._message(f"{len(copied)} linha(s) copiada(s).")

    def paste(self, *, after: bool):
        rows = self.selected_rows()
        if not self.grelha.clipboard:
            self._message("Copie primeiro as linhas (Ctrl+C).")
            return
        anchor = (rows[-1] if after else rows[0]) if rows else len(self.grelha.rows) - 1
        created = self.grelha.paste_rows(anchor, after=after)
        self.model.refresh()
        self._message(f"{len(created)} linha(s) nova(s) inserida(s).")

    def delete_rows(self):
        rows = self.selected_rows()
        if rows:
            self.grelha.delete_rows(rows)
            self.model.refresh()

    def clear_cells(self):
        cleared = self.grelha.clear_cells(self.selected_cells())
        self.model.refresh()
        self._message(f"{cleared} célula(s) limpa(s).")

    def restore_rows(self):
        rows = self.selected_rows()
        if rows:
            self.grelha.restore_rows(rows)
            self.model.refresh()

    def undo(self):
        if self.grelha.undo():
            self.model.refresh()
            self._message("Operação anulada.")
        else:
            self._message("Nada para anular.")

    def redo(self):
        if self.grelha.redo():
            self.model.refresh()
            self._message("Operação refeita.")

    def _context_menu(self, pos):
        menu = QMenu(self)
        for key in ("undo", "redo", "copy", "paste_before", "paste_after", "delete", "clear", "restore"):
            if key == "copy":
                menu.addSeparator()
            menu.addAction(self.actions[key])
        menu.exec(self.view.viewport().mapToGlobal(pos))

    # ---- filtros -------------------------------------------------------------

    def _filter_menu(self, col: int):
        values = sorted({self.model.text(r, col) or VAZIO for r in range(self.model.rowCount())})
        active = self.proxy.allowed.get(col)
        menu = QMenu(self)
        box = QWidget()
        box_layout = QVBoxLayout(box)
        search = QLineEdit()
        search.setPlaceholderText("Procurar…")
        search.setToolTip("Filtrar a lista de valores.")
        box_layout.addWidget(search)
        listing = QListWidget()
        listing.setMinimumSize(280, 260)
        listing.setToolTip("Marque os valores a mostrar.")
        for value in values:
            item = QListWidgetItem(value)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked if active is None or value in active
                               else Qt.CheckState.Unchecked)
            listing.addItem(item)
        box_layout.addWidget(listing)
        search.textChanged.connect(lambda text: [
            listing.item(i).setHidden(text.lower() not in listing.item(i).text().lower())
            for i in range(listing.count())])
        row = QHBoxLayout()
        for label, state in (("Todos", Qt.CheckState.Checked), ("Nenhum", Qt.CheckState.Unchecked)):
            button = QPushButton(label)
            button.setToolTip(f"Marcar {label.lower()} os valores visíveis.")
            button.clicked.connect(lambda _=False, s=state: [
                listing.item(i).setCheckState(s) for i in range(listing.count())
                if not listing.item(i).isHidden()])
            row.addWidget(button)
        ok = QPushButton("OK")
        ok.setToolTip("Aplicar o filtro a esta coluna.")
        row.addWidget(ok)
        box_layout.addLayout(row)
        action = QWidgetAction(menu)
        action.setDefaultWidget(box)
        menu.addAction(action)

        def apply():
            chosen = {listing.item(i).text() for i in range(listing.count())
                      if listing.item(i).checkState() == Qt.CheckState.Checked}
            self.proxy.set_filter(col, None if chosen == set(values) else chosen)
            self._mark_header(col)
            menu.close()

        ok.clicked.connect(apply)
        header = self.view.horizontalHeader()
        menu.exec(header.mapToGlobal(QPoint(header.sectionViewportPosition(col), header.height())))

    def _mark_header(self, col: int = 0):
        self.model.filtered = set(self.proxy.allowed)
        self.model.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, self.model.columnCount() - 1)
        self._update_summary()

    def _clear_filters(self):
        self.proxy.refilter(self.proxy.allowed.clear)
        self._mark_header()

    def _toggle_only_changes(self, checked):
        self.proxy.refilter(lambda: setattr(self.proxy, "only_changes", checked))
        self._update_summary()

    # ---- resumo -------------------------------------------------------------

    def _message(self, text):
        self._update_summary(extra=text)

    def _update_summary(self, *_, extra=""):
        cells, removed, new = self.grelha.summary()
        filters = ", ".join(self.model.column_name(c) for c in self.proxy.allowed)
        self.summary.setText(
            f"{len(self.grelha.rows)} linhas ({self.proxy.rowCount()} visíveis) · a levar ao Excel: "
            f"{cells} células, {removed} linhas eliminadas, {new} linhas novas"
            + (f" · filtros: {filters}" if filters else "") + (f" · {extra}" if extra else ""))
