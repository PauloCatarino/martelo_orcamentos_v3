"""Botão de socorro do utilizador: "aconteceu-me isto, vejam lá o que foi".

Junta o contexto e as últimas linhas do diário de bordo num ficheiro e deixa
enviá-lo por email (Outlook, o mesmo caminho dos orçamentos) ou gravá-lo para
mandar à mão. O utilizador vê exatamente o que vai enviar — nada segue sem ele
carregar no botão.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)

from sqlalchemy.exc import SQLAlchemyError

from app.config.versao import VERSAO_APLICACAO
from app.core import diario_bordo
from app.db.session import SessionLocal
from app.services import reporte_problema_service as svc
from app.services.email_service import carregar_email_config, enviar_email
from app.ui import tema


class ReportarProblemaDialog(QDialog):
    """Pack what happened and send it to whoever supports the Martelo."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.setWindowTitle("Reportar problema")
        self.setModal(True)
        self.resize(1000, 700)

        contexto = diario_bordo.contexto_atual()

        intro = QLabel(
            "Descreva o que estava a fazer e o que esperava que acontecesse. "
            "O Martelo junta a esta descrição o registo das últimas ações "
            "(menus, obras e avisos) para ser mais fácil perceber o que correu mal."
        )
        intro.setWordWrap(True)

        self.contexto_label = QLabel(
            f"Utilizador: {contexto.get('utilizador', '-')}   ·   "
            f"Menu: {contexto.get('menu', '-')}   ·   "
            f"Obra: {contexto.get('obra', '-')}   ·   "
            f"Versão: {VERSAO_APLICACAO}"
        )
        self.contexto_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")
        self.contexto_label.setWordWrap(True)

        self.descricao_text = QPlainTextEdit()
        self.descricao_text.setPlaceholderText(
            "Ex.: exportei o PDF do CUT-RITE da obra 1349 e o ficheiro não apareceu na pasta."
        )
        self.descricao_text.setToolTip("O que estava a fazer quando o problema aconteceu")
        self.descricao_text.setMaximumHeight(120)
        self.descricao_text.textChanged.connect(self._atualizar_pre_visualizacao)

        self.email_input = QLineEdit(self._email_por_defeito())
        self.email_input.setPlaceholderText("email de quem trata do Martelo")
        self.email_input.setToolTip(
            "Para onde vai o relatório. O valor por defeito vem de "
            "Configurações → Caminhos do Sistema (email_suporte_v3)."
        )

        email_linha = QHBoxLayout()
        email_linha.addWidget(QLabel("Enviar para:"))
        email_linha.addWidget(self.email_input, stretch=1)

        self.pre_visualizacao = QPlainTextEdit()
        self.pre_visualizacao.setReadOnly(True)
        self.pre_visualizacao.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.pre_visualizacao.setToolTip("Isto é exatamente o que vai ser enviado")

        self.enviar_button = QPushButton("Enviar por email")
        self.enviar_button.setToolTip("Enviar o relatório pelo Outlook")
        self.enviar_button.clicked.connect(self._enviar)

        self.gravar_button = QPushButton("Gravar ficheiro...")
        self.gravar_button.setToolTip("Gravar o relatório para o enviar à mão")
        self.gravar_button.clicked.connect(self._gravar)

        self.copiar_button = QPushButton("Copiar")
        self.copiar_button.setToolTip("Copiar o relatório para a área de transferência")
        self.copiar_button.clicked.connect(self._copiar)

        self.pasta_button = QPushButton("Abrir pasta do registo")
        self.pasta_button.setToolTip(str(diario_bordo.caminho_diario()))
        self.pasta_button.clicked.connect(self._abrir_pasta)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.clicked.connect(self.reject)

        self.status_label = QLabel("")
        self.status_label.setObjectName("reportarProblemaStatus")

        botoes = QHBoxLayout()
        botoes.addWidget(self.gravar_button)
        botoes.addWidget(self.copiar_button)
        botoes.addWidget(self.pasta_button)
        botoes.addStretch()
        botoes.addWidget(self.enviar_button)
        botoes.addWidget(self.fechar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(intro)
        layout.addWidget(self.contexto_label)
        layout.addWidget(QLabel("O que aconteceu:"))
        layout.addWidget(self.descricao_text)
        layout.addLayout(email_linha)
        layout.addWidget(QLabel("O que vai ser enviado:"))
        layout.addWidget(self.pre_visualizacao, stretch=1)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self._atualizar_pre_visualizacao()

    # ---- conteúdo ---------------------------------------------------------
    def _relatorio(self) -> str:
        return svc.montar_relatorio(
            self.descricao_text.toPlainText(), versao=VERSAO_APLICACAO
        )

    def _atualizar_pre_visualizacao(self) -> None:
        self.pre_visualizacao.setPlainText(self._relatorio())

    @staticmethod
    def _email_por_defeito() -> str:
        try:
            with SessionLocal() as session:
                return svc.email_suporte(session)
        except SQLAlchemyError:
            return ""

    # ---- ações ------------------------------------------------------------
    def _gravar(self) -> None:
        sugestao = str(Path.home() / svc.nome_do_relatorio())
        caminho, _ = QFileDialog.getSaveFileName(
            self, "Gravar relatório de problema", sugestao, "Texto (*.txt)"
        )
        if not caminho:
            return
        destino = Path(caminho)
        try:
            destino.write_text(self._relatorio(), encoding="utf-8")
        except OSError as erro:
            QMessageBox.critical(
                self, "Reportar problema", f"Não foi possível gravar o ficheiro.\n\n{erro}"
            )
            return
        self.status_label.setText(f"Relatório gravado em {destino}")

    def _copiar(self) -> None:
        QApplication.clipboard().setText(self._relatorio())
        self.status_label.setText("Relatório copiado para a área de transferência.")

    def _abrir_pasta(self) -> None:
        pasta = diario_bordo.caminho_diario().parent
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta)))

    def _enviar(self) -> None:
        destino = self.email_input.text().strip()
        if not destino:
            QMessageBox.warning(
                self,
                "Reportar problema",
                "Falta o email de destino. Preencha-o aqui ou em Configurações → "
                "Caminhos do Sistema (email_suporte_v3).",
            )
            return

        try:
            anexo = svc.gravar_relatorio(self._relatorio())
        except OSError as erro:
            QMessageBox.critical(
                self, "Reportar problema", f"Não foi possível preparar o relatório.\n\n{erro}"
            )
            return

        contexto = diario_bordo.contexto_atual()
        assunto = (
            f"[Martelo V3] Problema — {contexto.get('utilizador', '-')} "
            f"— {contexto.get('menu', '-')}"
        )
        corpo = (
            "<p>Relatório de problema do Martelo V3 (o detalhe vai em anexo).</p>"
            f"<p><b>Utilizador:</b> {contexto.get('utilizador', '-')}<br>"
            f"<b>Menu:</b> {contexto.get('menu', '-')}<br>"
            f"<b>Obra:</b> {contexto.get('obra', '-')}<br>"
            f"<b>Versão:</b> {VERSAO_APLICACAO}</p>"
            f"<pre>{self.descricao_text.toPlainText().strip()}</pre>"
        )

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            with SessionLocal() as session:
                config = carregar_email_config(session)
            enviar_email(destino, assunto, corpo, [str(anexo)], config=config)
        except Exception as erro:  # noqa: BLE001 - email falha por muitas razões
            QApplication.restoreOverrideCursor()
            QMessageBox.critical(
                self,
                "Reportar problema",
                "Não foi possível enviar o email.\n\n"
                f"{erro}\n\nO relatório ficou gravado em:\n{anexo}",
            )
            return
        QApplication.restoreOverrideCursor()

        diario_bordo.registar_acao("Reportou um problema", destino)
        QMessageBox.information(
            self,
            "Reportar problema",
            f"Relatório enviado para {destino}.\n\nCópia local:\n{anexo}",
        )
        self.accept()
