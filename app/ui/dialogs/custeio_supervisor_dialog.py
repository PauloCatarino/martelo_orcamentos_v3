"""Assistente de resolução de erros de custeio (Fase 1).

Mostra, para uma linha com erro grave, o problema, o *porquê* do alerta e uma
*sugestão* de correção, e oferece botões que levam o utilizador à origem do
problema (abrir as operações da linha, focar a linha). É acompanhante, não
corretor: não altera dados — encaminha o utilizador para o sítio certo.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from app.services.custeio_auditoria_service import CRITICO
from app.services.custeio_supervisor import DiagnosticoLinha
from app.ui import tema


class CusteioSupervisorDialog(QDialog):
    def __init__(
        self,
        descricao_linha: str,
        diagnosticos: Sequence[DiagnosticoLinha],
        navegar: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._navegar = navegar
        self.setWindowTitle("Assistente de resolução")
        self.setMinimumSize(560, 460)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        intro = QLabel(
            "Encontrei o que pode dar um custo errado nesta linha. Vê o porquê e a "
            "sugestão; usa os botões para ir ao sítio onde corriges."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")
        layout.addWidget(intro)

        alvo = QLabel(descricao_linha)
        alvo.setWordWrap(True)
        alvo.setStyleSheet(f"font-weight: bold; color: {tema.CASTANHO_ESCURO};")
        layout.addWidget(alvo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        conteudo = QWidget()
        self._lista = QVBoxLayout(conteudo)
        self._lista.setContentsMargins(0, 0, 0, 0)
        self._lista.setSpacing(10)
        for diagnostico in diagnosticos:
            self._lista.addWidget(self._cartao(diagnostico))
        self._lista.addStretch()
        scroll.setWidget(conteudo)
        layout.addWidget(scroll, stretch=1)

        fechar = QPushButton("Fechar")
        fechar.setToolTip("Fechar o assistente sem navegar.")
        fechar.clicked.connect(self.reject)
        rodape = QHBoxLayout()
        rodape.addStretch()
        rodape.addWidget(fechar)
        layout.addLayout(rodape)

    def _cartao(self, diagnostico: DiagnosticoLinha) -> QWidget:
        cartao = QFrame()
        cartao.setObjectName("cartaoDiagnostico")
        grave = diagnostico.severidade == CRITICO
        cor_borda = tema.TEXTO_ERRO if grave else tema.TEXTO_AVISO
        cartao.setStyleSheet(
            f"QFrame#cartaoDiagnostico {{ background: {tema.BEGE_CLARO};"
            f" border: 1px solid {tema.CINZA_CASTANHO};"
            f" border-left: 4px solid {cor_borda}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(cartao)
        lay.setSpacing(6)

        cabecalho = QHBoxLayout()
        etiqueta = QLabel("GRAVE" if grave else "AVISO")
        etiqueta.setStyleSheet(
            f"color: #FFFFFF; background: {cor_borda}; padding: 1px 8px;"
            " border-radius: 8px; font-weight: bold; font-size: 11px;"
        )
        cabecalho.addWidget(etiqueta)
        categoria = QLabel(diagnostico.categoria)
        categoria.setStyleSheet(f"font-weight: bold; color: {tema.CASTANHO_ESCURO};")
        cabecalho.addWidget(categoria)
        cabecalho.addStretch()
        lay.addLayout(cabecalho)

        lay.addWidget(self._linha_texto("Alerta:", diagnostico.mensagem))
        lay.addWidget(self._linha_texto("Porquê:", diagnostico.porque))
        lay.addWidget(self._linha_texto("Como resolver:", diagnostico.sugestao))

        if diagnostico.origens:
            origens_label = QLabel("Ir para a origem do problema:")
            origens_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; margin-top: 2px;")
            lay.addWidget(origens_label)
            botoes = QHBoxLayout()
            for origem in diagnostico.origens:
                botao = QPushButton(origem.titulo)
                botao.setToolTip(origem.descricao)
                botao.clicked.connect(
                    lambda _checked=False, chave=origem.chave: self._ir(chave)
                )
                botoes.addWidget(botao)
            botoes.addStretch()
            lay.addLayout(botoes)

        return cartao

    @staticmethod
    def _linha_texto(rotulo: str, texto: str) -> QWidget:
        widget = QWidget()
        lay = QVBoxLayout(widget)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(1)
        titulo = QLabel(rotulo)
        titulo.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; font-size: 11px;")
        corpo = QLabel(texto)
        corpo.setWordWrap(True)
        corpo.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(titulo)
        lay.addWidget(corpo)
        return widget

    def _ir(self, chave: str) -> None:
        # Fecha o assistente e navega para a origem, para o utilizador ver o alvo.
        self.accept()
        self._navegar(chave)
