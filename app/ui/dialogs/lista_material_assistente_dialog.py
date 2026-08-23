"""Configuração inicial, explícita, do Assistente Lista Material."""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.lista_material_assistente_service import (
    AssistantConfig,
    MODULES,
    normalize_text,
)


MODULE_LABELS = {
    "vista_vertical": "Vista Vertical",
    "remate_teto": "Remate Teto",
    "rodape_frente": "Rodapé Frente",
    "agrupamentos": "Agrupamentos",
    "cnc_fresar": "CNC_FRESAR",
    "notas": "Notas",
    "puxadores": "Puxadores",
    "lacagem_formal": "Lacagem formal (Tipo_Lacagem)",
    "validacao_placa_orla": "Validação placa–orla",
    "sugestoes_material": "Sugestões de material",
    "exportacao_pdf": "Exportação PDF",
}


class ListaMaterialAssistenteDialog(QDialog):
    def __init__(self, config: AssistantConfig, parent=None) -> None:
        super().__init__(parent)
        self._base = config
        self.setWindowTitle("Assistente Lista Material — configuração da obra")
        self.setMinimumWidth(650)
        self.setMinimumHeight(700)
        screen = QGuiApplication.primaryScreen()
        available_height = (
            screen.availableGeometry().height() if screen is not None else 960
        )
        self.resize(680, max(760, min(available_height - 60, 900)))

        title = QLabel(f"Cliente: {config.client or 'não indicado'}")
        title.setStyleSheet("font-size: 16px; font-weight: 600;")

        catalog = QLabel(config.board_catalog_message)
        catalog.setWordWrap(True)
        catalog.setStyleSheet(
            "padding: 8px; border-radius: 4px; "
            + ("background: #e7f6ea;" if config.board_catalog_available else "background: #fff4d6;")
        )

        form = QFormLayout()
        self.handle_input = QLineEdit(config.handle)
        self.handle_input.setPlaceholderText("Ex.: Puxador J H1030, TIC-TAC…")
        self.handle_input.setToolTip(
            "Sugestão geral da obra. Pode ficar vazia e pode ser alterada por Artigo/RP no Excel."
        )
        form.addRow("Puxador da obra:", self.handle_input)
        self.cnc_note_input = QLineEdit(config.cnc_note)
        self.cnc_note_input.setPlaceholderText("Ex.: CNC RECORTE L")
        self.cnc_note_input.setToolTip(
            "Texto curto a escrever em Notas quando uma orla contém CNC_FRESAR. "
            "Pode ficar vazio quando não pretende nota automática."
        )
        form.addRow("Nota para CNC_FRESAR:", self.cnc_note_input)
        self.handle_exceptions_input = QPlainTextEdit()
        self.handle_exceptions_input.setPlaceholderText(
            "Uma exceção por linha, por exemplo:\nRP_03=Puxador J H1030\nARTIGO_12=TIC-TAC"
        )
        self.handle_exceptions_input.setPlainText(
            "\n".join(f"{key}={value}" for key, value in config.handle_exceptions.items())
        )
        self.handle_exceptions_input.setToolTip(
            "Substituições do puxador geral por Artigo ou RP, no formato CHAVE=valor"
        )
        self.handle_exceptions_input.setMaximumHeight(90)
        form.addRow("Exceções Artigo/RP:", self.handle_exceptions_input)

        group = QGroupBox("Módulos ativos nesta obra")
        module_layout = QVBoxLayout(group)
        self.module_checks: dict[str, QCheckBox] = {}
        for name in MODULES:
            check = QCheckBox(MODULE_LABELS.get(name, name))
            check.setChecked(bool(config.modules.get(name, True)))
            check.setToolTip(
                "Ativar ou desativar este módulo apenas para a configuração apresentada."
            )
            module_layout.addWidget(check)
            self.module_checks[name] = check

        self.save_defaults_check = QCheckBox("Guardar como minhas preferências para este cliente")
        self.save_defaults_check.setToolTip(
            "Quando marcado, esta configuração fica pré-preenchida nas próximas obras deste cliente."
        )

        self.status_label = QLabel(
            "O assistente só cria propostas. Cada alteração continuará visível e dependente da sua decisão."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #5c6570;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Criar Excel")
        buttons.button(QDialogButtonBox.StandardButton.Ok).setToolTip(
            "Criar o livro com esta configuração e as folhas técnicas do assistente."
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Cancelar")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setToolTip("Não criar o Excel")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.addWidget(title)
        content_layout.addWidget(catalog)
        content_layout.addLayout(form)
        content_layout.addWidget(group)
        content_layout.addWidget(self.save_defaults_check)
        content_layout.addWidget(self.status_label)
        content_layout.addWidget(buttons)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        layout = QVBoxLayout(self)
        layout.addWidget(scroll)

    def config(self) -> AssistantConfig:
        modules = {name: check.isChecked() for name, check in self.module_checks.items()}
        exceptions: dict[str, str] = {}
        cnc_note = self.cnc_note_input.text().strip()
        for line in self.handle_exceptions_input.toPlainText().splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() and value.strip():
                # Compatibilidade com configurações já introduzidas no formato
                # CNC_FRESAR=CNC RECORTE L no campo antigo de exceções.
                if normalize_text(key) == "CNC_FRESAR":
                    cnc_note = value.strip()
                else:
                    exceptions[key.strip()] = value.strip()
        return AssistantConfig(
            user_id=self._base.user_id,
            client=self._base.client,
            modules=modules,
            handle=self.handle_input.text().strip(),
            handle_exceptions=exceptions,
            cnc_note=cnc_note,
            formal_lacquering=modules.get("lacagem_formal", False),
            board_catalog_available=self._base.board_catalog_available,
            board_catalog_message=self._base.board_catalog_message,
        )

    def save_as_defaults(self) -> bool:
        return self.save_defaults_check.isChecked()
