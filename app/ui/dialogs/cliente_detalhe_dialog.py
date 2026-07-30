"""Ficha do cliente: tudo à vista, só os emails de envio é que se editam.

Os dados do cliente vêm do PHC e são só-leitura no Martelo — mudá-los aqui
daria a ideia errada de que o PHC ficava alterado. As duas listas de envio,
essas, são escolha do Martelo e é o que este diálogo deixa mexer.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.domain.clientes_simplex import validar_simplex
from app.ui import tema

LARGURA = 780
ALTURA_MINIMA = 620
#: Teto para a zona dos dados do cliente, para a ficha não crescer sem fim.
ALTURA_MAX_DADOS = 640


class ClienteDetalheDialog(QDialog):
    """Show one customer and edit only the two Martelo mailing lists."""

    def __init__(self, cliente, parent=None) -> None:
        super().__init__(parent)

        self.cliente = cliente
        self.setWindowTitle(f"Cliente — {cliente.nome}")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        layout.addWidget(self._cabecalho())
        layout.addWidget(self._grupo_envio())

        dados = self._grupo_dados()
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(dados)
        # Abrir já com os campos todos à vista; o scroll fica só como recurso
        # para ecrãs pequenos.
        area.setMinimumHeight(min(dados.sizeHint().height() + 8, ALTURA_MAX_DADOS))
        layout.addWidget(area, stretch=1)

        self.status_label = QLabel("")
        self.status_label.setObjectName("clientesStatus")
        self.status_label.setWordWrap(True)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        guardar = self.buttons.button(QDialogButtonBox.StandardButton.Save)
        guardar.setText("Guardar")
        guardar.setToolTip("Guardar os emails de envio deste cliente")
        cancelar = self.buttons.button(QDialogButtonBox.StandardButton.Cancel)
        cancelar.setText("Fechar")
        cancelar.setToolTip("Fechar sem guardar")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        layout.addWidget(self.buttons)
        layout.addWidget(self.status_label)

        self.resize(LARGURA, self._altura_para_mostrar_tudo())

    def _altura_para_mostrar_tudo(self) -> int:
        """Altura que mostra a ficha inteira sem passar do ecrã disponível."""
        ecra = QGuiApplication.primaryScreen()
        limite = (
            int(ecra.availableGeometry().height() * 0.92) if ecra is not None else 900
        )
        return min(max(ALTURA_MINIMA, self.sizeHint().height()), limite)

    # ---- valores editados -------------------------------------------------
    def email_orcamentos(self) -> str | None:
        return self.ed_email_orcamentos.text().strip() or None

    def email_projeto_producao(self) -> str | None:
        return self.ed_email_producao.text().strip() or None

    def houve_alteracoes(self) -> bool:
        return (
            self.email_orcamentos() != (self.cliente.email_orcamentos or None)
            or self.email_projeto_producao()
            != (self.cliente.email_projeto_producao or None)
        )

    # ---- construção -------------------------------------------------------
    def _cabecalho(self) -> QWidget:
        painel = QWidget()
        layout = QVBoxLayout(painel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        titulo = QLabel(self.cliente.nome)
        titulo.setStyleSheet(
            f"color: {tema.CASTANHO_ESCURO}; font-size: 15px; font-weight: bold;"
        )
        titulo.setWordWrap(True)

        tipo = "Temporário (só no Martelo)" if self.cliente.is_temporary else "PHC (oficial)"
        num = self.cliente.num_cliente_phc or "—"
        subtitulo = QLabel(f"{tipo}  ·  Nº Cliente PHC: {num}")
        subtitulo.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; font-size: 11px;")

        layout.addWidget(titulo)
        layout.addWidget(subtitulo)
        return painel

    def _grupo_envio(self) -> QGroupBox:
        grupo = QGroupBox("Envio de emails (configurado no Martelo)")
        form = QFormLayout(grupo)

        self.ed_email_orcamentos = QLineEdit(self.cliente.email_orcamentos or "")
        self.ed_email_orcamentos.setPlaceholderText(
            "Vazio — é usado o email do cliente"
        )
        self.ed_email_orcamentos.setToolTip(
            "Para onde vai o email do orçamento deste cliente.\n"
            "Vários endereços separados por ponto e vírgula (;).\n"
            "Se ficar vazio, é usado o email geral que vem do PHC."
        )

        self.ed_email_producao = QLineEdit(
            self.cliente.email_projeto_producao or ""
        )
        self.ed_email_producao.setPlaceholderText(
            "Vazio — é usado o email do cliente"
        )
        self.ed_email_producao.setToolTip(
            "Para onde vai o projeto de produção deste cliente.\n"
            "Vários endereços separados por ponto e vírgula (;).\n"
            "Se ficar vazio, é usado o email geral que vem do PHC."
        )

        form.addRow("Email envio orçamentos", self.ed_email_orcamentos)
        form.addRow("Email envio projeto produção", self.ed_email_producao)

        nota = QLabel(
            "São os únicos campos editáveis: os restantes dados vêm do PHC e "
            "são atualizados por «Atualizar PHC», que nunca apaga estes dois."
        )
        nota.setWordWrap(True)
        nota.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; font-size: 11px;")
        form.addRow(nota)

        return grupo

    def _grupo_dados(self) -> QGroupBox:
        grupo = QGroupBox("Dados do cliente (só leitura — vêm do PHC)")
        form = QFormLayout(grupo)

        campos = [
            ("Nome", self.cliente.nome, "Nome completo do cliente, tal como no PHC."),
            (
                "Simplex (nome abreviado)",
                self.cliente.nome_simplex or "",
                "Nome abreviado do PHC (NOME2). Dá o nome à pasta da obra, ao "
                "plano CUT-RITE e à encomenda iMos — máximo 19 caracteres.",
            ),
            ("Nº Cliente PHC", self.cliente.num_cliente_phc or "", "Número do cliente no PHC."),
            ("Morada", self.cliente.morada or "", "Morada registada no PHC."),
            ("Email", self.cliente.email or "", "Email geral do cliente, vindo do PHC."),
            ("Página WEB", self.cliente.pagina_web or "", "Site do cliente."),
            ("Telefone", self.cliente.telefone or "", "Telefone registado no PHC."),
            ("Telemóvel", self.cliente.telemovel or "", "Telemóvel registado no PHC."),
            ("Info 1", self.cliente.info_1 or "", "Observações vindas do PHC."),
            ("Info 2", self.cliente.info_2 or "", "Observações do Martelo."),
        ]

        for etiqueta, valor, dica in campos:
            campo = QLineEdit(valor)
            campo.setReadOnly(True)
            campo.setCursorPosition(0)
            campo.setToolTip(dica)
            campo.setStyleSheet(
                f"background-color: {tema.BEGE_AREIA}; color: {tema.CASTANHO_ESCURO};"
            )
            form.addRow(etiqueta, campo)

            if etiqueta.startswith("Simplex"):
                self._avisar_simplex(form, campo)

        return grupo

    def _avisar_simplex(self, form: QFormLayout, campo: QLineEdit) -> None:
        """Diz logo aqui o que está mal no nome abreviado (e onde se corrige)."""
        erro = validar_simplex(self.cliente.nome_simplex, nome_cliente=self.cliente.nome)
        if erro is None:
            return

        campo.setStyleSheet(
            f"background-color: {tema.VERMELHO_SUAVE}; color: {tema.VERMELHO_ESCURO};"
        )
        campo.setToolTip(erro)

        aviso = QLabel(erro.split("\n\n")[0])
        aviso.setWordWrap(True)
        aviso.setStyleSheet(f"color: {tema.TEXTO_ERRO}; font-size: 11px;")
        aviso.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow("", aviso)
