"""Confirmar o envio das horas de um mês à contabilidade.

Aparece sozinho no dia 2 de cada mês, às 9h20 (ou quando o Martelo abrir
depois disso), e também pelo botão da página. Mostra a folha do mês e o
resumo, e só envia quando a pessoa carrega em «Enviar à contabilidade». O
envio em si (PDF, Outlook, registo) é feito por quem abre o diálogo.
"""

from __future__ import annotations

import html
from collections.abc import Callable
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.domain import registo_horas as regra
from app.services.registo_horas_service import EnvioMes
from app.ui import tema

ACAO_ENVIAR = "enviar"
ACAO_CORRIGIR = "corrigir"
ACAO_ADIAR = "adiar"

COLUNAS = ("Dia", "Tipo", "Horário", "Normais", "Extra", "Subs. Alim.", "Observações")


def corpo_html(texto: str) -> str:
    """O texto simples do diálogo → HTML do email (parágrafos e quebras)."""
    paragrafos = [p for p in texto.strip().split("\n\n") if p.strip()]
    return "".join(
        "<p>" + "<br>".join(html.escape(linha) for linha in p.split("\n")) + "</p>"
        for p in paragrafos
    )


class RegistoHorasEnvioDialog(QDialog):
    def __init__(
        self,
        parent: QWidget | None,
        *,
        nome: str,
        ano: int,
        mes: int,
        dias: list[regra.LinhaDia],
        em_falta: list[date],
        destinatario: str,
        ja_enviado: EnvioMes | None = None,
        automatico: bool = False,
        ver_pdf: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.acao: str | None = None
        self._ver_pdf = ver_pdf
        resumo = regra.resumir_mes(dias)
        self.setWindowTitle(f"Registo de Horas — enviar {regra.nome_mes(ano, mes)}")
        self.setMinimumSize(900, 760)

        titulo = QLabel(f"Horas de {regra.nome_mes(ano, mes)} — {nome}")
        titulo.setStyleSheet(
            f"font-size: 15px; font-weight: bold; color: {tema.CASTANHO_ESCURO};"
        )
        if automatico:
            texto = (
                f"É dia {regra.DIA_ENVIO}: as horas de {regra.nome_mes(ano, mes)} vão "
                "seguir para a contabilidade. Confira a folha; se for preciso mudar "
                "alguma coisa, carregue em «Corrigir primeiro» e envie depois pelo "
                "botão «Enviar à contabilidade…» do Registo de Horas."
            )
        else:
            texto = (
                f"Confira a folha de {regra.nome_mes(ano, mes)} antes de a enviar à "
                "contabilidade."
            )
        explicacao = QLabel(texto)
        explicacao.setWordWrap(True)

        avisos = QVBoxLayout()
        if ja_enviado is not None:
            aviso = QLabel(
                f"Este mês já foi enviado a {ja_enviado.enviado_em:%d/%m/%Y %H:%M} "
                f"para {ja_enviado.destinatario}. Se enviar outra vez, segue a folha "
                "como está agora."
            )
            aviso.setWordWrap(True)
            aviso.setStyleSheet(f"color: {tema.TEXTO_AVISO};")
            avisos.addWidget(aviso)
        if em_falta:
            falta = QLabel(
                f"Atenção: {len(em_falta)} dia(s) útil(eis) sem horas registadas: "
                f"{regra.lista_de_dias(em_falta)}."
            )
            falta.setWordWrap(True)
            falta.setStyleSheet(f"color: {tema.TEXTO_ERRO}; font-weight: bold;")
            avisos.addWidget(falta)

        # ---- resumo ------------------------------------------------------
        caixa_resumo = QGroupBox("Resumo do mês")
        grelha = QGridLayout(caixa_resumo)
        linhas_resumo = resumo.linhas_relatorio()
        for linha, (rotulo, valor) in enumerate(linhas_resumo):
            etiqueta = QLabel(rotulo)
            numero = QLabel(valor)
            numero.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if linha == len(linhas_resumo) - 2:
                etiqueta.setStyleSheet("font-weight: bold;")
                numero.setStyleSheet("font-weight: bold;")
            elif linha == len(linhas_resumo) - 1:
                # O subsídio de alimentação: euros, à parte do total de horas.
                for rotulo_subsidio in (etiqueta, numero):
                    rotulo_subsidio.setStyleSheet(
                        f"background-color: {tema.OCRE_SUAVE}; color: {tema.OCRE_ESCURO};"
                        " font-weight: bold; padding: 2px 4px;"
                    )
            grelha.addWidget(etiqueta, linha, 0)
            grelha.addWidget(numero, linha, 1)

        # ---- dias --------------------------------------------------------
        self.tabela = QTableWidget(len(dias), len(COLUNAS))
        self.tabela.setHorizontalHeaderLabels(list(COLUNAS))
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabela.setAlternatingRowColors(True)
        self.tabela.horizontalHeader().setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        self.tabela.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)
        self.tabela.setToolTip("Os dias registados neste mês, tal como seguem na folha.")
        for linha, dia in enumerate(dias):
            valores = (
                f"{dia.data.day:02d} {regra.SEMANA_CURTO[dia.data.weekday()]}",
                regra.NOMES_TIPOS[dia.tipo].replace(" (desconta)", ""),
                dia.horario,
                regra.formatar_horas(dia.normais) if dia.normais else "",
                regra.formatar_total(dia.extra, com_mais=dia.tipo == regra.TIPO_UTIL)
                if dia.extra
                else "",
                dia.subsidio_folha,
                dia.observacoes_folha(),
            )
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if coluna == 4 and dia.extra < 0:
                    item.setForeground(Qt.GlobalColor.darkRed)
                self.tabela.setItem(linha, coluna, item)
        self.tabela.resizeColumnsToContents()

        self.pdf_button = QPushButton("Ver a folha em PDF")
        self.pdf_button.setToolTip("Abrir a folha deste mês em PDF, tal como vai no email")
        self.pdf_button.clicked.connect(self._abrir_pdf)
        self.pdf_button.setEnabled(ver_pdf is not None)

        meio = QHBoxLayout()
        meio.addWidget(caixa_resumo)
        meio.addWidget(self.tabela, stretch=1)

        # ---- email -------------------------------------------------------
        self.para_edit = QLineEdit(destinatario)
        self.para_edit.setToolTip(
            "Para quem segue (a contabilidade). Fica também uma cópia no seu email."
        )
        self.assunto_edit = QLineEdit(regra.assunto_email(nome, ano, mes))
        self.assunto_edit.setToolTip("Assunto do email")
        self.mensagem_edit = QPlainTextEdit(regra.corpo_email(nome, ano, mes, resumo))
        self.mensagem_edit.setToolTip("Texto do email; a folha em PDF vai em anexo.")
        self.mensagem_edit.setMinimumHeight(120)
        caixa_email = QGroupBox("Email")
        form = QFormLayout(caixa_email)
        form.addRow("Para", self.para_edit)
        form.addRow("Assunto", self.assunto_edit)
        form.addRow("Mensagem", self.mensagem_edit)

        # ---- botões ------------------------------------------------------
        self.enviar_button = QPushButton("Enviar à contabilidade")
        self.enviar_button.setToolTip("Enviar já o email com a folha em PDF em anexo")
        self.enviar_button.setAutoDefault(False)
        self.enviar_button.clicked.connect(lambda: self._fechar(ACAO_ENVIAR))
        self.corrigir_button = QPushButton("Corrigir primeiro")
        self.corrigir_button.setToolTip(
            "Não envia: abre o mês no Registo de Horas para corrigir. Depois envie "
            "pelo botão «Enviar à contabilidade…»."
        )
        self.corrigir_button.setAutoDefault(False)
        self.corrigir_button.clicked.connect(lambda: self._fechar(ACAO_CORRIGIR))
        self.adiar_button = QPushButton("Lembrar amanhã" if automatico else "Cancelar")
        self.adiar_button.setToolTip(
            "Não envia agora; o aviso volta amanhã."
            if automatico
            else "Fechar sem enviar"
        )
        self.adiar_button.setAutoDefault(False)
        self.adiar_button.clicked.connect(
            lambda: self._fechar(ACAO_ADIAR if automatico else None)
        )
        botoes = QHBoxLayout()
        botoes.addWidget(self.pdf_button)
        botoes.addStretch()
        botoes.addWidget(self.enviar_button)
        botoes.addWidget(self.corrigir_button)
        botoes.addWidget(self.adiar_button)

        layout = QVBoxLayout(self)
        layout.addWidget(titulo)
        layout.addWidget(explicacao)
        layout.addLayout(avisos)
        layout.addLayout(meio, stretch=3)
        layout.addWidget(caixa_email, stretch=2)
        layout.addLayout(botoes)

    def _abrir_pdf(self) -> None:
        if self._ver_pdf is not None:
            self._ver_pdf()

    def _fechar(self, acao: str | None) -> None:
        if acao == ACAO_ENVIAR and not self.para_edit.text().strip():
            self.para_edit.setFocus()
            self.para_edit.setPlaceholderText("Indique o email da contabilidade")
            return
        self.acao = acao
        if acao is None:
            self.reject()
        else:
            self.accept()

    def destinatario(self) -> str:
        return self.para_edit.text().strip()

    def assunto(self) -> str:
        return self.assunto_edit.text().strip()

    def mensagem_html(self) -> str:
        return corpo_html(self.mensagem_edit.toPlainText())
