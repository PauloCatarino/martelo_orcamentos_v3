"""Centro de Exportação PDF da Lista Material."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.orm import Session

from app.models.lista_material_assistente import ListaMaterialPdfExportacao

from app.services.lista_material_pdf_service import (
    PdfExportCancelled,
    PdfPresetService,
    export_pdf_documents,
    inspect_pdf_documents,
    normalize_pdf_identifiers,
    sync_pdf_document_registry,
)


class ListaMaterialPdfDialog(QDialog):
    def __init__(
        self,
        session: Session,
        *,
        workbook_path: Path,
        production_id: int,
        user_id: int,
        client: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.session = session
        self.workbook_path = Path(workbook_path)
        self.production_id = int(production_id)
        self.user_id = int(user_id)
        self.client = client
        self.preset_service = PdfPresetService(session)
        sync_pdf_document_registry(session)
        self.states = inspect_pdf_documents(self.workbook_path)
        self.checks: dict[str, QCheckBox] = {}
        self._last_result = None

        self.setWindowTitle("Exportar documentação")
        self.resize(820, 640)

        title = QLabel("Centro de Exportação PDF")
        title.setStyleSheet("font-size: 18px; font-weight: 600;")
        subtitle = QLabel(str(self.workbook_path))
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #5c6570;")

        self.preset_combo = QComboBox()
        self.preset_combo.setToolTip(
            "Aplicar uma seleção guardada apenas para este utilizador e cliente"
        )
        self.preset_combo.currentIndexChanged.connect(self._apply_preset)

        self.preset_name = QLineEdit()
        self.preset_name.setPlaceholderText("Ex.: Pacote Produção JF_VIVA")
        self.preset_name.setToolTip("Nome com que esta seleção ficará guardada")
        save_preset = QPushButton("Guardar preset")
        save_preset.setToolTip("Guardar seleção e opções como preferência deste utilizador/cliente")
        save_preset.clicked.connect(self._save_preset)
        self.default_preset_check = QCheckBox("Predefinido")
        self.default_preset_check.setToolTip(
            "Carregar automaticamente este preset ao abrir o Centro de Exportação PDF"
        )
        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset:"))
        preset_row.addWidget(self.preset_combo, 2)
        preset_row.addWidget(self.preset_name, 2)
        preset_row.addWidget(self.default_preset_check)
        preset_row.addWidget(save_preset)

        categories: dict[str, QGroupBox] = {}
        category_layouts: dict[str, QVBoxLayout] = {}
        documents_widget = QWidget()
        documents_layout = QGridLayout(documents_widget)
        for state in self.states:
            category = state.document.category
            if category not in categories:
                box = QGroupBox(category)
                box_layout = QVBoxLayout(box)
                categories[category] = box
                category_layouts[category] = box_layout
                pos = len(categories) - 1
                documents_layout.addWidget(box, pos // 2, pos % 2)
            label = state.document.name
            if not state.available:
                label += " — dados em falta"
            check = QCheckBox(label)
            check.setEnabled(state.available)
            check.setToolTip(state.reason or f"Exportar {state.document.name} individualmente ou no pacote")
            category_layouts[category].addWidget(check)
            self.checks[state.document.identifier] = check

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(documents_widget)

        select_all = QPushButton("Selecionar tudo disponível")
        select_all.setToolTip("Marcar todos os documentos que têm dados neste livro")
        select_all.clicked.connect(lambda: self._select_all(True))
        clear_all = QPushButton("Limpar seleção")
        clear_all.setToolTip("Desmarcar todos os documentos")
        clear_all.clicked.connect(lambda: self._select_all(False))
        select_row = QHBoxLayout()
        select_row.addWidget(select_all)
        select_row.addWidget(clear_all)
        select_row.addStretch()

        self.destination = QLineEdit(str(self.workbook_path.parent))
        self.destination.setToolTip(
            "Pasta onde serão criados os PDFs; se já existirem ficheiros com o "
            "mesmo nome, o Martelo pergunta se quer substituir"
        )
        choose_folder = QPushButton("Escolher pasta…")
        choose_folder.setToolTip("Selecionar a pasta de destino")
        choose_folder.clicked.connect(self._choose_folder)
        destination_row = QHBoxLayout()
        destination_row.addWidget(QLabel("Destino:"))
        destination_row.addWidget(self.destination, 1)
        destination_row.addWidget(choose_folder)

        self.separate_check = QCheckBox("Exportar ficheiros separados")
        self.separate_check.setChecked(True)
        self.separate_check.setToolTip("Criar um PDF por documento selecionado")
        self.package_check = QCheckBox("Criar pacote combinado")
        self.package_check.setToolTip("Criar também um único PDF pela ordem apresentada")
        self.open_folder_check = QCheckBox("Abrir pasta no fim")
        self.open_folder_check.setChecked(True)
        self.open_folder_check.setToolTip("Abrir a pasta de destino depois da exportação")
        options = QHBoxLayout()
        options.addWidget(self.separate_check)
        options.addWidget(self.package_check)
        options.addWidget(self.open_folder_check)
        options.addStretch()

        self.status_label = QLabel("Selecione os documentos. Os indisponíveis mostram a explicação na dica.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #5c6570;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        export_button = QPushButton("Exportar")
        export_button.setToolTip(
            "Exportar a seleção; PDFs já existentes só são substituídos se confirmar"
        )
        export_button.clicked.connect(self._export)
        close_button = QPushButton("Fechar")
        close_button.setToolTip("Fechar o centro de exportação")
        close_button.clicked.connect(self.accept)
        action_row = QHBoxLayout()
        action_row.addStretch()
        action_row.addWidget(export_button)
        action_row.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(preset_row)
        layout.addLayout(select_row)
        layout.addWidget(scroll, 1)
        layout.addLayout(destination_row)
        layout.addLayout(options)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress)
        layout.addLayout(action_row)

        self._reload_presets(apply_default=True)

    def _reload_presets(
        self, *, select_id: int | None = None, apply_default: bool = False
    ) -> None:
        presets = self.preset_service.list(user_id=self.user_id, client=self.client)
        selected_index = 0
        self.preset_combo.blockSignals(True)
        self.preset_combo.clear()
        self.preset_combo.addItem("Sem preset", None)
        for preset in presets:
            self.preset_combo.addItem(preset.nome, preset)
            if select_id is not None and preset.id == select_id:
                selected_index = self.preset_combo.count() - 1
            elif select_id is None and apply_default and preset.predefinido:
                selected_index = self.preset_combo.count() - 1
        self.preset_combo.setCurrentIndex(selected_index)
        self.preset_combo.blockSignals(False)
        if selected_index:
            self._apply_preset()

    def _select_all(self, checked: bool) -> None:
        for check in self.checks.values():
            if check.isEnabled():
                check.setChecked(checked)

    def _selected_ids(self) -> list[str]:
        return [identifier for identifier, check in self.checks.items() if check.isChecked()]

    def _apply_preset(self) -> None:
        preset = self.preset_combo.currentData()
        if preset is None:
            self.preset_name.clear()
            self.default_preset_check.setChecked(False)
            return
        try:
            identifiers = normalize_pdf_identifiers(
                json.loads(preset.documentos_json or "[]")
            )
        except (TypeError, json.JSONDecodeError):
            identifiers = set()
        for identifier, check in self.checks.items():
            check.setChecked(check.isEnabled() and identifier in identifiers)
        self.separate_check.setChecked(bool(preset.exportar_separados))
        self.package_check.setChecked(bool(preset.criar_pacote))
        self.preset_name.setText(preset.nome)
        self.default_preset_check.setChecked(bool(preset.predefinido))

    def _save_preset(self) -> None:
        try:
            preset = self.preset_service.save(
                user_id=self.user_id,
                client=self.client,
                name=self.preset_name.text(),
                identifiers=self._selected_ids(),
                export_separate=self.separate_check.isChecked(),
                create_package=self.package_check.isChecked(),
                make_default=self.default_preset_check.isChecked(),
            )
        except ValueError as exc:
            self.status_label.setText(str(exc))
            return
        self._reload_presets(select_id=preset.id)
        sufixo = " e definido como predefinido" if preset.predefinido else ""
        self.status_label.setText(
            f"Preset guardado apenas para este utilizador e cliente{sufixo}."
        )

    def _choose_folder(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Pasta de destino", self.destination.text())
        if selected:
            self.destination.setText(selected)

    def _on_progress(self, message: str, current: int, total: int) -> None:
        self.status_label.setText(message)
        self.progress.setValue(int(current * 100 / max(total, 1)))
        QApplication.processEvents()

    def _confirmar_substituicao(self, existentes: tuple[Path, ...]) -> bool:
        """Pergunta o que fazer aos PDFs que já estão na pasta de destino."""
        nomes = "\n".join(f"- {caminho.name}" for caminho in existentes[:12])
        if len(existentes) > 12:
            nomes += f"\n- (e mais {len(existentes) - 12} ficheiro(s))"
        box = QMessageBox(self)
        box.setWindowTitle("PDFs já existentes")
        box.setIcon(QMessageBox.Question)
        box.setText("Já existem PDFs com estes nomes na pasta de destino:")
        box.setInformativeText(
            f"{nomes}\n\nQuer substituir os ficheiros existentes?\n"
            "Se não substituir, os atuais ficam como estão e os novos são "
            "gravados com _2 no fim do nome."
        )
        substituir = box.addButton("Substituir", QMessageBox.YesRole)
        manter = box.addButton("Manter e criar _2", QMessageBox.NoRole)
        cancelar = box.addButton("Cancelar", QMessageBox.RejectRole)
        box.setDefaultButton(manter)
        box.exec()
        escolhido = box.clickedButton()
        if escolhido is cancelar or escolhido is None:
            raise PdfExportCancelled()
        return escolhido is substituir

    def _export(self) -> None:
        if not self.separate_check.isChecked() and not self.package_check.isChecked():
            self.status_label.setText("Ative ficheiros separados, pacote combinado, ou ambos.")
            return
        try:
            self._last_result = export_pdf_documents(
                self.workbook_path,
                Path(self.destination.text().strip()),
                self._selected_ids(),
                export_separate=self.separate_check.isChecked(),
                create_package=self.package_check.isChecked(),
                progress_callback=self._on_progress,
                conflict_resolver=self._confirmar_substituicao,
            )
        except PdfExportCancelled:
            self.progress.setValue(0)
            self.status_label.setText("Exportação cancelada. Nada foi alterado na pasta.")
            return
        except Exception as exc:
            self.status_label.setText("A exportação falhou.")
            QMessageBox.critical(self, "Exportar documentação", str(exc))
            return
        try:
            self.session.add(
                ListaMaterialPdfExportacao(
                    producao_id=self.production_id,
                    user_id=self.user_id,
                    workbook_path=str(self.workbook_path),
                    destino=self.destination.text().strip(),
                    documentos_json=json.dumps(self._selected_ids(), ensure_ascii=False),
                    resultado_json=json.dumps(
                        {
                            "ficheiros": [str(path) for path in self._last_result.files],
                            "pacote": str(self._last_result.package or ""),
                            "erros": list(self._last_result.errors),
                        },
                        ensure_ascii=False,
                    ),
                    estado="parcial" if self._last_result.errors else "concluida",
                    concluida_em=datetime.now(),
                )
            )
            self.session.commit()
        except Exception as exc:
            self.session.rollback()
            QMessageBox.warning(
                self,
                "Exportar documentação",
                "Os PDFs foram criados, mas não foi possível guardar o "
                f"histórico da exportação.\n\nDetalhe: {exc}",
            )
        count = len(self._last_result.files) + int(self._last_result.package is not None)
        self.progress.setValue(100)
        self.status_label.setText(
            f"Exportação concluída: {count} ficheiro(s). "
            f"Erros: {len(self._last_result.errors)}."
        )
        if self._last_result.errors:
            QMessageBox.warning(self, "Exportar documentação", "\n".join(self._last_result.errors))
        if self.open_folder_check.isChecked():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.destination.text().strip()))
