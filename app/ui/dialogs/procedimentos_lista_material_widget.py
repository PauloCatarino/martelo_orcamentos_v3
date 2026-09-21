"""Separador «Procedimentos da listagem» da Análise da Lista Material.

O trabalho que se fazia à mão na LISTAGEM_CUT_RITE depois do AUTOMATION —
sobretudo nas obras lowcost (prédios com muitos roupeiros iguais): tirar o
CNC_FRESAR das orlas, notas de lacagem/puxador/piso, juntar Vista Vertical,
Remate Teto e Rodapé em barras, trocar uma orla em toda a obra.

O motor é o do antigo «Analisar/Completar Lista Material», que ficou sem
chamada desde a versão 1.0.15. Aqui decide-se por REGRA (em bloco) ou peça a
peça, e a configuração da obra (puxador, nota CNC...) aparece onde tem efeito.
Nada se aplica sem decisão; antes de aplicar fica uma cópia do Excel.
"""
from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFormLayout, QHBoxLayout, QHeaderView,
    QLabel, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.services import analise_lista_material_service as svc
from app.services.lista_material_assistente_service import (
    EDGE_FIELDS, AssistantDecision, ListaMaterialAssistantService, WorkbookAudit,
    apply_workbook_decisions, edge_replacement_suggestions, normalize_text,
    read_material_table, rule_group,
)
from app.services.permission_service import PERMISSAO_CORRIGIR_LISTA_MATERIAL
from app.services.warehouse_board_catalog import WoodstoreBoardCatalogProvider
from app.ui.dialogs.lista_material_assistente_dialog import ListaMaterialAssistenteDialog
from app.ui.dialogs.lista_material_revisao_dialog import ListaMaterialRevisaoDialog
from app.ui.widgets.combo_sem_scroll import ComboSemScroll

MODULE_LABELS = {
    "cnc_fresar": "CNC_FRESAR", "notas": "Notas", "puxadores": "Puxadores",
    "vista_vertical": "Vista Vertical", "remate_teto": "Remate Teto",
    "rodape_frente": "Rodapé Frente",
}


def group_label(suggestion) -> str:
    label = rule_group(suggestion.kind)
    if suggestion.kind == "orla_em_massa":
        label += f": {suggestion.original} → {suggestion.suggested or '(vazio)'}"
    return label


def group_suggestions(suggestions) -> list[tuple[str, list]]:
    groups: dict[str, list] = {}
    for suggestion in suggestions:
        groups.setdefault(group_label(suggestion), []).append(suggestion)
    return list(groups.items())


def accepted_decisions(groups, selected: set[str]) -> tuple[list[AssistantDecision], int]:
    """Aceitar em bloco as regras marcadas; devolve (decisões, conflitos saltados).

    As sugestões bloqueantes (sem valor seguro) ficam para a revisão peça a peça.
    Duas regras sobre a mesma célula: fica a primeira da lista.
    """
    decisions, seen, skipped = [], set(), 0
    for label, suggestions in groups:
        if label not in selected:
            continue
        for suggestion in suggestions:
            if suggestion.blocking:
                continue
            if not (suggestion.suggested or suggestion.allow_blank or suggestion.delete_row):
                continue
            cell = (suggestion.row_number, suggestion.field)
            if cell in seen:
                skipped += 1
                continue
            seen.add(cell)
            decisions.append(AssistantDecision(suggestion, "aceitar", suggestion.suggested))
    return decisions, skipped


class ProcedimentosListaMaterialWidget(QWidget):
    def __init__(self, session, *, user, permissions, workbook_path, obra_info,
                 catalog_provider, on_applied, parent=None):
        super().__init__(parent)
        self.session, self.user, self.permissions = session, user, permissions
        self.path = Path(workbook_path)
        self.obra_info = dict(obra_info or {})
        self.catalog_provider = catalog_provider
        self.on_applied = on_applied
        self.config = None
        self.rows, self.columns, self.groups = [], (), []
        self.bulk_specs: list[dict] = []
        self.analysed_hash = ""
        self.can_fix = bool(permissions.get(PERMISSAO_CORRIGIR_LISTA_MATERIAL))

        layout = QVBoxLayout(self)
        intro = QLabel(
            "O que se fazia à mão na LISTAGEM_CUT_RITE, pensado sobretudo para obras lowcost "
            "(muitos artigos iguais): CNC_FRESAR, notas de lacagem/puxador/piso, barras de Vista "
            "Vertical, Remate Teto e Rodapé, e trocas de orla em toda a obra. Marque as regras a "
            "aplicar em bloco, ou reveja peça a peça. Nada muda sem a sua decisão e fica uma cópia "
            "do Excel antes de aplicar.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.config_label = QLabel("")
        self.config_label.setWordWrap(True)
        layout.addWidget(self.config_label)

        top = QHBoxLayout()
        self._button(top, "Configuração da obra…", self._configure,
                     "Puxador da obra, nota para CNC_FRESAR, exceções por Artigo/RP e regras ativas. "
                     "Pode guardar como preferências para este cliente.")
        self.analyse_button = self._button(
            top, "Analisar procedimentos", self.analyse,
            "Ler a LISTAGEM_CUT_RITE guardada e propor as alterações, agrupadas por regra.")
        self.bulk_button = self._button(
            top, "Substituir orla em massa…", self._bulk_edge,
            "Trocar uma orla por outra em toda a obra (p. ex. PVC_0.4_LINHO → PVC_1.0_LINHO), "
            "escolhendo os lados e as peças.")
        top.addStretch()
        layout.addLayout(top)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Aplicar", "Regra", "Alterações", "Peças", "Para confirmar", "Exemplo"])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        for col, width in enumerate((70, 420, 95, 70, 110)):
            self.table.setColumnWidth(col, width)
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.review_button = self._button(
            bottom, "Rever peça a peça…", self._review,
            "Abrir as propostas das regras marcadas, peça a peça, para aceitar, editar ou manter.")
        self.apply_button = self._button(
            bottom, "Aplicar regras marcadas", self._apply,
            "Aceitar em bloco as propostas seguras das regras marcadas. As que precisam de "
            "confirmação ficam para «Rever peça a peça».")
        bottom.addStretch()
        layout.addLayout(bottom)
        self.status = QLabel("Ainda não analisado. Carregue em «Analisar procedimentos».")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        for button in (self.review_button, self.apply_button, self.bulk_button):
            button.setEnabled(False)

    @staticmethod
    def _button(layout, text, callback, tooltip):
        button = QPushButton(text)
        button.setToolTip(tooltip)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    # ---- configuração -------------------------------------------------------

    def _service(self):
        catalog = self.catalog_provider() or []
        return ListaMaterialAssistantService(
            self.session, board_catalog=WoodstoreBoardCatalogProvider(lambda: catalog))

    def load_config(self):
        if self.config is not None:
            return self.config
        service = self._service()
        user_id = int(getattr(self.user, "id", 0) or 0)
        client = self.obra_info.get("cliente_simplex") or self.obra_info.get("cliente", "")
        production_id = self.obra_info.get("producao_id")
        if production_id:
            self.config = service.resolve_work_config(
                production_id=int(production_id), user_id=user_id, client=client,
                production_description=self.obra_info.get("descricao_producao", ""))
        else:
            self.config = service.resolve_config(
                user_id=user_id, client=client,
                production_description=self.obra_info.get("descricao_producao", ""))
        self._show_config()
        return self.config

    def _show_config(self):
        c = self.config
        active = [label for key, label in MODULE_LABELS.items() if c.modules.get(key, True)]
        self.config_label.setText(
            f"Puxador: {c.handle or '—'} · Nota CNC_FRESAR: {c.cnc_note or '—'} · "
            f"Exceções Artigo/RP: {len(c.handle_exceptions)} · Regras ativas: {', '.join(active) or 'nenhuma'}")

    def _configure(self):
        try:
            config = self.load_config()
            dialog = ListaMaterialAssistenteDialog(config, self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            self.config = dialog.config()
            service = self._service()
            if dialog.save_as_defaults():
                service.save_profile_defaults(self.config)
            if self.obra_info.get("producao_id"):
                service.create_work_snapshot(
                    production_id=int(self.obra_info["producao_id"]),
                    workbook_path=self.path, config=self.config)
            self._show_config()
            if self.rows:
                self.analyse()
        except (SQLAlchemyError, ValueError, RuntimeError) as error:
            self.session.rollback()
            QMessageBox.warning(self, "Configuração da obra", str(error))

    # ---- análise ------------------------------------------------------------

    def analyse(self):
        try:
            config = self.load_config()
            before = svc.fingerprint(self.path)
            self.columns, rows = read_material_table(self.path)
            if svc.fingerprint(self.path) != before:
                raise ValueError("O Excel mudou durante a leitura. Repita a análise.")
            self.rows = rows
            self.analysed_hash = before
            suggestions = self._service().analyze_rows(rows, config=config)
            for spec in self.bulk_specs:
                suggestions += edge_replacement_suggestions(rows, **spec)
            self.groups = group_suggestions(suggestions)
            self._render()
        except Exception as error:  # Excel bloqueado, formato, base de dados
            self.session.rollback()
            self.status.setText(f"Não foi possível analisar: {error}")
            QMessageBox.warning(self, "Procedimentos da listagem", str(error))

    def _render(self):
        self.table.setRowCount(len(self.groups))
        rows_by_number = {row.row_number: row for row in self.rows}
        cells = pieces_total = 0
        for i, (label, suggestions) in enumerate(self.groups):
            blocking = sum(1 for s in suggestions if s.blocking)
            changes = sum(1 for s in suggestions if not s.delete_row)
            removed = sum(1 for s in suggestions if s.delete_row)
            pieces = len({s.row_number for s in suggestions})
            cells += changes
            pieces_total += pieces
            check = QTableWidgetItem()
            check.setFlags(check.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            check.setCheckState(Qt.CheckState.Unchecked if blocking == len(suggestions)
                                else Qt.CheckState.Checked)
            check.setToolTip("Marcar para aplicar esta regra em bloco.")
            self.table.setItem(i, 0, check)
            first = next((s for s in suggestions if not s.blocking), suggestions[0])
            row = rows_by_number.get(first.row_number)
            example = (f"{row.description if row else ''} (linha {first.row_number}): "
                       + ("juntar/remover linha" if first.delete_row else
                          f"{first.field} «{first.original}» → «{first.suggested}»"))
            values = (label, f"{changes}" + (f" + {removed} linhas juntas" if removed else ""),
                      str(pieces), str(blocking) if blocking else "—", example)
            for col, value in enumerate(values, 1):
                item = QTableWidgetItem(value)
                item.setToolTip(value if col != 5 else first.reason)
                self.table.setItem(i, col, item)
        has = bool(self.groups)
        self.review_button.setEnabled(has)
        self.apply_button.setEnabled(has and self.can_fix)
        self.bulk_button.setEnabled(bool(self.rows) and self.can_fix)
        self.status.setText(
            f"{len(self.rows)} peças analisadas · {len(self.groups)} regras com propostas · "
            f"{cells} células a alterar." if has else
            f"{len(self.rows)} peças analisadas · nenhuma proposta com a configuração atual.")

    def _selected(self) -> set[str]:
        return {self.groups[i][0] for i in range(self.table.rowCount())
                if self.table.item(i, 0).checkState() == Qt.CheckState.Checked}

    # ---- aplicar ------------------------------------------------------------

    def _check_unchanged(self):
        if svc.fingerprint(self.path) != self.analysed_hash:
            raise ValueError("O Excel mudou desde a análise. Volte a analisar antes de aplicar.")

    def _apply(self):
        try:
            decisions, skipped = accepted_decisions(self.groups, self._selected())
            if not decisions:
                self.status.setText("Nenhuma regra marcada com propostas seguras.")
                return
            removed = sum(1 for d in decisions if d.suggestion.delete_row)
            answer = QMessageBox.question(
                self, "Aplicar regras marcadas",
                f"Vão ser alteradas {len(decisions) - removed} células e juntadas {removed} linhas "
                "na LISTAGEM_CUT_RITE.\n\nFica uma cópia do Excel antes de aplicar. Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
            applied = self._write(decisions)
            self.status.setText(
                f"{applied} alterações aplicadas." + (f" {skipped} ignoradas por outra regra já "
                                                      "mexer na mesma célula." if skipped else ""))
        except Exception as error:
            self.session.rollback()
            QMessageBox.warning(self, "Aplicar regras marcadas", str(error))

    def _review(self):
        try:
            selected = self._selected()
            suggestions = tuple(s for label, group in self.groups if label in selected for s in group)
            if not suggestions:
                self.status.setText("Marque pelo menos uma regra para rever.")
                return
            audit = WorkbookAudit(
                workbook_path=self.path, rows=tuple(self.rows), suggestions=suggestions,
                blocking=tuple(s for s in suggestions if s.blocking),
                board_catalog_message=self.config.board_catalog_message, columns=self.columns)
            review = ListaMaterialRevisaoDialog(audit, self)
            if review.exec() != QDialog.DialogCode.Accepted:
                return
            if not self.can_fix:
                raise ValueError("O administrador não atribuiu a permissão para corrigir a Lista Material.")
            applied = self._write(review.decisions())
            self.status.setText(f"{applied} alterações aplicadas peça a peça.")
        except Exception as error:
            self.session.rollback()
            QMessageBox.warning(self, "Rever peça a peça", str(error))

    def _write(self, decisions) -> int:
        if not self.can_fix:
            raise ValueError("O administrador não atribuiu a permissão para corrigir a Lista Material.")
        self._check_unchanged()
        backup = svc.backup_path(svc.writable_workbook(self.path), "antes_procedimentos")
        shutil.copy2(self.path, backup)
        # Numa obra lowcost são centenas de células: ~45 s no Excel real (1568).
        self.status.setText(f"A aplicar {len(decisions)} alterações no Excel… pode demorar um minuto.")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        QApplication.processEvents()
        try:
            applied = apply_workbook_decisions(
                self.path, decisions, user_name=getattr(self.user, "username", "") or "Martelo",
                expected_hash=self.analysed_hash)
        finally:
            QApplication.restoreOverrideCursor()
        self._learn(decisions)
        self.on_applied()
        self.analyse()
        return applied

    def _learn(self, decisions):
        """Histórico e aprendizagem placa–orla; uma falha aqui não desfaz o Excel."""
        production_id = self.obra_info.get("producao_id")
        if not production_id:
            return
        try:
            service = self._service()
            suggestions = tuple(d.suggestion for d in decisions)
            audit = WorkbookAudit(
                workbook_path=self.path, rows=tuple(self.rows), suggestions=suggestions,
                blocking=tuple(s for s in suggestions if s.blocking),
                board_catalog_message=self.config.board_catalog_message, columns=self.columns)
            execution = service.record_audit(
                production_id=int(production_id), user_id=int(getattr(self.user, "id", 0) or 0),
                audit=audit, kind="procedimentos")
            service.record_decisions(execution_id=execution.id, decisions=decisions,
                                     rows=self.rows, config=self.config)
        except SQLAlchemyError:
            self.session.rollback()

    # ---- orla em massa ------------------------------------------------------

    def _bulk_edge(self):
        dialog = OrlaEmMassaDialog(self.rows, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        spec = dialog.spec()
        if not spec:
            return
        self.bulk_specs.append(spec)
        self.analyse()


class OrlaEmMassaDialog(QDialog):
    """Escolher a orla a trocar, a nova, os lados e as peças; mostra quantas células."""

    def __init__(self, rows, parent=None):
        super().__init__(parent)
        self.rows = list(rows)
        self.setWindowTitle("Substituir orla em massa")
        self.resize(640, 560)
        counts = Counter(edge for row in self.rows for edge in row.edges.values()
                         if edge and "CNC" not in normalize_text(edge))
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.origem = ComboSemScroll()
        self.origem.setToolTip("A orla que está hoje na lista.")
        for edge, count in counts.most_common():
            self.origem.addItem(f"{edge}  ({count} células)", edge)
        self.destino = ComboSemScroll()
        self.destino.setEditable(True)
        self.destino.setToolTip("A orla nova. Pode escrever um nome que ainda não esteja na lista; "
                                "vazio = tirar a orla.")
        self.destino.addItems(sorted(counts))
        self.destino.setCurrentText("")
        form.addRow("Orla atual:", self.origem)
        form.addRow("Nova orla:", self.destino)
        sides = QHBoxLayout()
        self.sides = {}
        for side in EDGE_FIELDS:
            box = QCheckBox(side)
            box.setChecked(True)
            box.setToolTip(f"Trocar também no lado {side}.")
            box.toggled.connect(self._refresh)
            sides.addWidget(box)
            self.sides[side] = box
        form.addRow("Lados:", sides)
        layout.addLayout(form)
        layout.addWidget(QLabel("Peças (desmarque as que devem manter a orla atual):"))
        self.pieces = QListWidget()
        self.pieces.setToolTip("Só as peças que têm a orla escolhida.")
        self.pieces.itemChanged.connect(self._refresh)
        layout.addWidget(self.pieces, 1)
        self.preview = QLabel("")
        layout.addWidget(self.preview)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Propor substituição")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setToolTip(
            "Acrescentar esta troca às propostas; só se aplica depois, com as outras regras.")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.origem.currentIndexChanged.connect(self._fill_pieces)
        self.destino.currentTextChanged.connect(self._refresh)
        self._fill_pieces()

    def _fill_pieces(self):
        edge = self.origem.currentData()
        counts = Counter(row.description for row in self.rows if edge in row.edges.values())
        self.pieces.blockSignals(True)
        self.pieces.clear()
        for description, count in sorted(counts.items()):
            item = QListWidgetItem(f"{description}  ({count})")
            item.setData(Qt.ItemDataRole.UserRole, description)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            self.pieces.addItem(item)
        self.pieces.blockSignals(False)
        self._refresh()

    def spec(self) -> dict | None:
        edge = self.origem.currentData()
        if not edge:
            return None
        return {
            "origem": edge,
            "destino": self.destino.currentText().strip(),
            "lados": tuple(side for side, box in self.sides.items() if box.isChecked()),
            "descricoes": tuple(
                self.pieces.item(i).data(Qt.ItemDataRole.UserRole)
                for i in range(self.pieces.count())
                if self.pieces.item(i).checkState() == Qt.CheckState.Checked),
        }

    def _refresh(self, *_):
        spec = self.spec()
        found = edge_replacement_suggestions(self.rows, **spec) if spec else []
        self.preview.setText(
            f"{len(found)} células em {len({s.row_number for s in found})} peças." if found
            else "Nenhuma célula a trocar com esta escolha.")
