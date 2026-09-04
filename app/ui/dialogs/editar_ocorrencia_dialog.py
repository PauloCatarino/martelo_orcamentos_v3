"""Abrir ou corrigir um ticket da obra."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from app.domain import ocorrencia_tipos as tipos
from app.ui import tema
from app.ui.widgets.faixa_anexos import FaixaAnexos
from app.ui.widgets.combo_sem_scroll import ComboSemScroll, SpinDuploSemScroll


class EditarOcorrenciaDialog(QDialog):
    """Form of one ticket: o que aconteceu, de que tipo é e de quem fica."""

    def __init__(
        self,
        parent=None,
        *,
        codigo_processo: str = "",
        ocorrencia=None,
        anexos=(),
        membros=(),
        pode_editar: bool = True,
    ) -> None:
        super().__init__(parent)

        self._ocorrencia = ocorrencia
        novo = ocorrencia is None

        referencia = "" if novo else tipos.rotulo_ticket(getattr(ocorrencia, "numero", None))
        titulo = "Novo ticket" if novo else f"Ticket {referencia}"
        self.setWindowTitle(f"{titulo} — {codigo_processo}" if codigo_processo else titulo)
        self.setModal(True)
        self.resize(760, 640)

        self.assunto_input = QLineEdit()
        self.assunto_input.setMaxLength(200)
        self.assunto_input.setPlaceholderText(
            "Resumo numa linha. Ex.: falta prateleira do roupeiro do quarto 2"
        )
        self.assunto_input.setToolTip("Como este ticket aparece na lista e no chat")

        self.tipo_combo = self._combo(tipos.TIPOS, "O que é este ticket — usado na avaliação de erros do ano")
        self.gravidade_combo = self._combo(tipos.GRAVIDADES, "Quanto é que isto pesa")
        self.origem_combo = self._combo(tipos.ORIGENS, "De onde veio o problema")
        self.estado_combo = self._combo(tipos.ESTADOS, "Em que pé está este ticket")

        self.responsavel_combo = ComboSemScroll()
        self.responsavel_combo.setEditable(True)
        self.responsavel_combo.setToolTip(
            "Quem vai dar continuidade. Para enviar o ticket pelo Teams, a "
            "pessoa precisa de endereço na Equipa."
        )
        self.responsavel_combo.addItem("", None)
        for membro in membros or ():
            self.responsavel_combo.addItem(membro.nome, int(membro.id))

        self.custo_input = SpinDuploSemScroll()
        self.custo_input.setRange(0.0, 999999.99)
        self.custo_input.setDecimals(2)
        self.custo_input.setSuffix(" €")
        self.custo_input.setSpecialValueText("—")
        self.custo_input.setToolTip("Custo estimado, se souber. Fica em branco a zero.")

        self.texto_input = QTextEdit()
        self.texto_input.setAcceptRichText(False)
        self.texto_input.setMinimumHeight(140)
        self.texto_input.setPlaceholderText(
            "Escreva o que aconteceu. Ex.: cliente diz que faltou uma dobradiça "
            "no roupeiro do quarto 2; combinado levar na próxima entrega."
        )
        self.texto_input.setToolTip("O que aconteceu nesta obra")

        self.anexos_widget = FaixaAnexos()
        self.anexos_widget.aviso.connect(self.status_label_texto)
        self.anexos_widget.carregar(anexos)

        self.colar_button = QPushButton("Colar imagem (Ctrl+V)")
        self.colar_button.setToolTip("Colar a foto que copiou do chat ou do explorador")
        self.colar_button.clicked.connect(self.anexos_widget.colar)

        self.escolher_button = QPushButton("Escolher fotos ou PDFs…")
        self.escolher_button.setToolTip(
            "Juntar fotos ou PDFs que já estão gravados no computador"
        )
        self.escolher_button.clicked.connect(self.anexos_widget.escolher_ficheiros)

        self.remover_button = QPushButton("Remover anexo")
        self.remover_button.setToolTip("Tirar do ticket o anexo selecionado")
        self.remover_button.clicked.connect(self.anexos_widget.remover_selecionados)

        self.gravar_button = QPushButton("Registar" if novo else "Gravar")
        self.gravar_button.setToolTip("Gravar este ticket na obra")
        self.gravar_button.setDefault(True)
        self.gravar_button.clicked.connect(self._validar_e_aceitar)

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.clicked.connect(self.reject)

        self.status_label = QLabel("")
        self.status_label.setObjectName("editarOcorrenciaStatus")
        self.status_label.setWordWrap(True)

        cabecalho = QLabel(
            "Um ticket é um assunto da obra: o que o cliente reportou, o que "
            "faltou, o que correu mal. As fotos ficam gravadas na pasta da obra."
        )
        cabecalho.setWordWrap(True)
        cabecalho.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        formulario = QFormLayout()
        formulario.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        formulario.addRow("Assunto", self.assunto_input)

        classificacao = QHBoxLayout()
        classificacao.addWidget(self.tipo_combo, stretch=2)
        classificacao.addWidget(QLabel("Gravidade"))
        classificacao.addWidget(self.gravidade_combo, stretch=1)
        classificacao.addWidget(QLabel("Origem"))
        classificacao.addWidget(self.origem_combo, stretch=1)
        formulario.addRow("Tipo", classificacao)

        encaminhamento = QHBoxLayout()
        encaminhamento.addWidget(self.responsavel_combo, stretch=2)
        encaminhamento.addWidget(QLabel("Estado"))
        encaminhamento.addWidget(self.estado_combo, stretch=1)
        encaminhamento.addWidget(QLabel("Custo"))
        encaminhamento.addWidget(self.custo_input, stretch=1)
        formulario.addRow("Responsável", encaminhamento)

        botoes_anexos = QHBoxLayout()
        botoes_anexos.addWidget(self.colar_button)
        botoes_anexos.addWidget(self.escolher_button)
        botoes_anexos.addWidget(self.remover_button)
        botoes_anexos.addStretch()

        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(self.gravar_button)
        botoes.addWidget(self.cancelar_button)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(cabecalho)
        layout.addLayout(formulario)
        layout.addWidget(QLabel("O que aconteceu"))
        layout.addWidget(self.texto_input, stretch=1)
        layout.addWidget(QLabel("Fotos e PDFs"))
        layout.addWidget(self.anexos_widget)
        layout.addLayout(botoes_anexos)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        if ocorrencia is not None:
            self._preencher(ocorrencia)
        if not pode_editar:
            self._bloquear_edicao()

    # ---- leitura ---------------------------------------------------------
    def dados(self) -> dict:
        """Return the ticket fields as the service expects them."""
        custo = self.custo_input.value()
        return {
            "assunto": self.assunto_input.text().strip(),
            "tipo": self.tipo_combo.currentData(),
            "gravidade": self.gravidade_combo.currentData(),
            "origem": self.origem_combo.currentData(),
            "estado": self.estado_combo.currentData(),
            "responsavel": self.responsavel_combo.currentText().strip(),
            "responsavel_membro_id": self._membro_id(),
            "custo_estimado": custo if custo > 0 else None,
            "texto": self.texto_input.toPlainText().strip(),
        }

    def anexos_pendentes(self):
        """Photos the user added but that are not on disk yet."""
        return self.anexos_widget.pendentes()

    def anexos_removidos(self):
        """Ids of the attachments the user took out."""
        return self.anexos_widget.removidos()

    def status_label_texto(self, texto: str) -> None:
        """Show a warning coming from the thumbnail strip."""
        self.status_label.setText(texto)

    # ---- apoio -----------------------------------------------------------
    @staticmethod
    def _combo(itens, tooltip: str) -> QComboBox:
        combo = ComboSemScroll()
        combo.setToolTip(tooltip)
        for item in itens:
            combo.addItem(item.rotulo, item.chave)
        return combo

    def _membro_id(self) -> int | None:
        """Id of the chosen team member — None when the name was typed by hand."""
        indice = self.responsavel_combo.currentIndex()
        if indice < 0:
            return None
        escrito = self.responsavel_combo.currentText().strip()
        if escrito != self.responsavel_combo.itemText(indice):
            return None
        dados = self.responsavel_combo.itemData(indice)
        return int(dados) if dados is not None else None

    def _preencher(self, ocorrencia) -> None:
        self.assunto_input.setText(str(getattr(ocorrencia, "assunto", "") or ""))
        self.texto_input.setPlainText(str(getattr(ocorrencia, "texto", "") or ""))
        self._selecionar(self.tipo_combo, tipos.normalizar_tipo(ocorrencia.tipo))
        self._selecionar(
            self.gravidade_combo, tipos.normalizar_gravidade(ocorrencia.gravidade)
        )
        self._selecionar(self.origem_combo, tipos.normalizar_origem(ocorrencia.origem))
        self._selecionar(self.estado_combo, tipos.normalizar_estado(ocorrencia.estado))
        self.responsavel_combo.setCurrentText(
            str(getattr(ocorrencia, "responsavel", "") or "")
        )
        custo = getattr(ocorrencia, "custo_estimado", None)
        if custo is not None:
            self.custo_input.setValue(float(custo))

    @staticmethod
    def _selecionar(combo: QComboBox, chave: str) -> None:
        indice = combo.findData(chave)
        if indice >= 0:
            combo.setCurrentIndex(indice)

    def _bloquear_edicao(self) -> None:
        """Only the author edits the text; anyone can move the state along."""
        for widget in (
            self.assunto_input,
            self.tipo_combo,
            self.gravidade_combo,
            self.origem_combo,
            self.responsavel_combo,
            self.custo_input,
            self.texto_input,
        ):
            widget.setEnabled(False)
        self.status_label.setText(
            "Este ticket foi escrito por outra pessoa: pode mudar o estado e "
            "juntar fotos, mas não alterar o texto."
        )

    def _validar_e_aceitar(self) -> None:
        if not self.texto_input.toPlainText().strip() and self.texto_input.isEnabled():
            self.status_label.setText("Escreva o que aconteceu antes de registar.")
            self.texto_input.setFocus()
            return
        self.accept()
