"""Dialog for reviewing and sending a budget email.

Serve os três emails que o Martelo manda com anexos — orçamento, ponto de
situação e projeto para o cliente. Por isso é aqui que se pesam os anexos:
o utilizador vê o total enquanto os junta e é avisado ANTES de enviar, em vez
de descobrir o problema no erro que volta do servidor.

É aqui também que se escolhe **responder** ao pedido do cliente em vez de
mandar um email novo, quando esse pedido está guardado na pasta do orçamento.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.domain.anexos_email import LIMITE_PADRAO_MB, medir_anexo, resumir_anexos
from app.services import email_resposta_service as resposta_svc
from app.ui import tema


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
        tamanho_max_mb: float = LIMITE_PADRAO_MB,
        emails_do_cliente: Sequence[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Enviar Orçamento por Email")
        self.resize(820, 540)
        self._pasta_inicial = pasta_inicial or ""
        self._tamanho_max_mb = float(tamanho_max_mb or LIMITE_PADRAO_MB)
        self._emails_do_cliente = [str(caminho) for caminho in emails_do_cliente or ()]
        # Guardados para repor se desligar o visto de responder.
        self._destinatario_proprio = destinatario
        self._assunto_proprio = assunto

        layout = QVBoxLayout(self)

        self._montar_linha_resposta(layout)

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
        self.list_anexos.setToolTip(
            "Ficheiros que serão anexados ao email, com o tamanho de cada um."
        )
        layout.addWidget(QLabel("Anexos:"))
        layout.addWidget(self.list_anexos, 1)

        self.lbl_tamanho = QLabel()
        self.lbl_tamanho.setToolTip(
            "Peso total dos anexos. Acima do limite o email costuma ser recusado "
            "pelo servidor."
        )
        layout.addWidget(self.lbl_tamanho)

        for path in anexos or []:
            self._acrescentar_anexo(path)

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

        self._atualizar_tamanho()
        self._aplicar_resposta()

    def destinatario(self) -> str:
        return self.ed_destinatario.text().strip()

    def cc(self) -> str:
        return self.ed_cc.text().strip()

    def assunto(self) -> str:
        return self.ed_assunto.text().strip()

    def corpo_html(self) -> str:
        return self.txt_corpo.toHtml()

    def anexos(self) -> list[str]:
        """Os caminhos dos anexos — o que se vê na lista é nome + tamanho."""
        return [
            str(self.list_anexos.item(i).data(Qt.ItemDataRole.UserRole))
            for i in range(self.list_anexos.count())
        ]

    def responder_a(self) -> str:
        """Caminho do email a responder, ou vazio se for um email novo."""
        if getattr(self, "check_responder", None) is None:
            return ""
        if not self.check_responder.isChecked():
            return ""
        return str(self.combo_resposta.currentData() or "")

    def accept(self) -> None:  # noqa: D102 - o aviso é a única diferença
        if self._confirmar_tamanho():
            super().accept()

    # ---- responder ao pedido do cliente -------------------------------------
    def _montar_linha_resposta(self, layout) -> None:
        """Linha do topo — só aparece se houver mesmo um email guardado."""
        self.check_responder = None
        if not self._emails_do_cliente:
            return

        self.check_responder = QCheckBox("Responder ao pedido do cliente:")
        self.check_responder.setChecked(True)
        self.check_responder.setToolTip(
            "Em vez de um email novo, responde ao pedido que o cliente enviou "
            "— com o email dele citado por baixo e no mesmo fio de conversa.\n"
            "Desligue para enviar um email novo, como antes."
        )

        self.combo_resposta = QComboBox()
        self.combo_resposta.setToolTip(
            "Emails guardados na pasta do orçamento, do mais recente para o "
            "mais antigo."
        )
        for caminho in self._emails_do_cliente:
            self.combo_resposta.addItem(Path(caminho).name, caminho)

        self.lbl_resposta = QLabel()
        self.lbl_resposta.setStyleSheet(f"color: {tema.TEXTO_OK};")

        linha = QHBoxLayout()
        linha.addWidget(self.check_responder)
        linha.addWidget(self.combo_resposta, 1)
        layout.addLayout(linha)
        layout.addWidget(self.lbl_resposta)

        self.check_responder.stateChanged.connect(lambda _=0: self._aplicar_resposta())
        self.combo_resposta.currentIndexChanged.connect(
            lambda _=0: self._aplicar_resposta()
        )

    def _aplicar_resposta(self) -> None:
        """Encher Destinatário e Assunto a partir do email do cliente."""
        if getattr(self, "check_responder", None) is None:
            return

        self.combo_resposta.setEnabled(self.check_responder.isChecked())
        if not self.check_responder.isChecked():
            self.ed_destinatario.setText(self._destinatario_proprio)
            self.ed_assunto.setText(self._assunto_proprio)
            self.lbl_resposta.setText("Vai um email novo, sem responder a nada.")
            self.lbl_resposta.setStyleSheet(f"color: {tema.TEXTO_AVISO};")
            return

        caminho = str(self.combo_resposta.currentData() or "")
        lido = resposta_svc.ler_email_do_cliente(caminho)
        if lido is None:
            # Sem Outlook ou ficheiro ilegível: não bloquear ninguém.
            self.check_responder.setChecked(False)
            self.lbl_resposta.setText(
                "Não consegui ler esse email guardado — o Martelo prepara um "
                "email novo."
            )
            self.lbl_resposta.setStyleSheet(f"color: {tema.TEXTO_ERRO};")
            return

        self.ed_destinatario.setText(lido.de or self._destinatario_proprio)
        self.ed_assunto.setText(
            resposta_svc.assunto_de_resposta(lido.assunto) or self._assunto_proprio
        )

        # A pasta pode ter emails que nada têm a ver com o pedido. Quando o
        # assunto não sugere um pedido de orçamento, dizê-lo — em vez de deixar
        # partir uma resposta para a conversa errada.
        if resposta_svc.parece_pedido(lido.assunto or lido.nome_ficheiro):
            self.lbl_resposta.setText(f"A responder a: {lido.etiqueta}")
            self.lbl_resposta.setStyleSheet(f"color: {tema.TEXTO_OK};")
        else:
            self.lbl_resposta.setText(
                f"A responder a: {lido.etiqueta} — o assunto não parece um "
                "pedido de orçamento; confirme se é este o email certo."
            )
            self.lbl_resposta.setStyleSheet(f"color: {tema.TEXTO_AVISO};")

    # ---- anexos -------------------------------------------------------------
    def _acrescentar_anexo(self, caminho: str) -> None:
        medida = medir_anexo(caminho)
        item = QListWidgetItem(medida.etiqueta)
        item.setData(Qt.ItemDataRole.UserRole, str(caminho))
        item.setToolTip(str(caminho))
        if not medida.existe:
            item.setForeground(Qt.GlobalColor.red)
        self.list_anexos.addItem(item)

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
                self._acrescentar_anexo(file_path)
                existentes.add(file_path)
        self._atualizar_tamanho()

    def _remover_anexos_selecionados(self) -> None:
        for item in self.list_anexos.selectedItems():
            self.list_anexos.takeItem(self.list_anexos.row(item))
        self._atualizar_tamanho()

    def _resumo_anexos(self):
        return resumir_anexos(self.anexos(), limite_mb=self._tamanho_max_mb)

    def _atualizar_tamanho(self) -> None:
        """Refrescar a linha com o peso total, já com a cor do estado."""
        resumo = self._resumo_anexos()
        if resumo.excede:
            cor = tema.TEXTO_ERRO
        elif resumo.em_falta:
            cor = tema.TEXTO_AVISO
        else:
            cor = tema.TEXTO_OK
        self.lbl_tamanho.setText(resumo.texto_barra)
        self.lbl_tamanho.setStyleSheet(f"color: {cor};")

    def _confirmar_tamanho(self) -> bool:
        """Avisar antes de enviar acima do limite. True = seguir em frente."""
        resumo = self._resumo_anexos()
        if not resumo.excede:
            return True

        caixa = QMessageBox(self)
        caixa.setIcon(QMessageBox.Icon.Warning)
        caixa.setWindowTitle("Anexos demasiado grandes")
        caixa.setText(resumo.mensagem_aviso())
        rever = caixa.addButton("Rever anexos", QMessageBox.ButtonRole.RejectRole)
        caixa.addButton("Enviar mesmo assim", QMessageBox.ButtonRole.AcceptRole)
        caixa.setDefaultButton(rever)
        caixa.exec()
        return caixa.clickedButton() is not rever
