"""Dialog for reviewing and sending a budget email."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class EmailOrcamentoDialog(QDialog):
    def __init__(
        self,
        parent=None,
        *,
        destinatario: str = "",
        cc: str = "",
        assunto: str = "",
        corpo: str = "",
        anexos: list[str] | None = None,
        pasta_inicial: str | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Enviar Orçamento por Email")
        self.resize(820, 540)
        self._pasta_inicial = pasta_inicial or ""

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.ed_destinatario = QLineEdit(destinatario)
        self.ed_destinatario.setToolTip(
            "Endereço de email do destinatário. Pode alterar antes de enviar."
        )
        self.ed_cc = QLineEdit(cc)
        self.ed_cc.setToolTip("Endereços em cópia, separados por ponto e vírgula.")
        self.ed_assunto = QLineEdit(assunto)
        self.ed_assunto.setToolTip("Assunto do email a enviar ao cliente.")
        form.addRow("Destinatário:", self.ed_destinatario)
        form.addRow("CC:", self.ed_cc)
        form.addRow("Assunto:", self.ed_assunto)
        layout.addLayout(form)

        corpo_label = QLabel("Corpo do email:")
        self.txt_corpo = QTextEdit()
        self.txt_corpo.setAcceptRichText(True)
        self.txt_corpo.setHtml(corpo or "")
        self.txt_corpo.setToolTip("Corpo do email em HTML/rich text.")
        layout.addWidget(corpo_label)
        layout.addWidget(self.txt_corpo, 1)

        self.list_anexos = QListWidget()
        self.list_anexos.setToolTip("Ficheiros que serão anexados ao email.")
        for path in anexos or []:
            self.list_anexos.addItem(path)
        layout.addWidget(QLabel("Anexos:"))
        layout.addWidget(self.list_anexos, 1)

        anexos_layout = QHBoxLayout()
        self.btn_adicionar = QPushButton("Adicionar anexo(s)")
        self.btn_adicionar.setToolTip("Adicionar ficheiros ao email.")
        self.btn_remover = QPushButton("Remover selecionado")
        self.btn_remover.setToolTip("Remover os anexos selecionados da lista.")
        anexos_layout.addWidget(self.btn_adicionar)
        anexos_layout.addWidget(self.btn_remover)
        anexos_layout.addStretch()
        layout.addLayout(anexos_layout)

        self.btn_adicionar.clicked.connect(self._adicionar_anexos)
        self.btn_remover.clicked.connect(self._remover_anexos_selecionados)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setText("Enviar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText(
            "Cancelar"
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def destinatario(self) -> str:
        return self.ed_destinatario.text().strip()

    def cc(self) -> str:
        return self.ed_cc.text().strip()

    def assunto(self) -> str:
        return self.ed_assunto.text().strip()

    def corpo_html(self) -> str:
        return self.txt_corpo.toHtml()

    def anexos(self) -> list[str]:
        return [self.list_anexos.item(i).text() for i in range(self.list_anexos.count())]

    def _adicionar_anexos(self) -> None:
        start_dir = self._pasta_inicial
        if not start_dir or not Path(start_dir).exists():
            start_dir = str(Path.home())
        files, _filter = QFileDialog.getOpenFileNames(
            self, "Selecionar anexos", start_dir
        )
        existentes = set(self.anexos())
        for file_path in files:
            if file_path and file_path not in existentes:
                self.list_anexos.addItem(file_path)
                existentes.add(file_path)

    def _remover_anexos_selecionados(self) -> None:
        for item in self.list_anexos.selectedItems():
            self.list_anexos.takeItem(self.list_anexos.row(item))
