"""Short, skippable startup introduction shown while MainWindow is prepared."""

from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from app.ui import tema


class IntroducaoWindow(QWidget):
    concluida = Signal()

    ETAPAS = (
        "A preparar o painel inicial…",
        "A organizar orçamentos e clientes…",
        "A ligar produção e auditorias…",
        "Martelo V3 pronto para trabalhar.",
    )

    def __init__(self, nome_utilizador: str = "") -> None:
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setFixedSize(660, 380)
        self._pronta = False
        self._terminou = False
        self._indice = 0
        self._relogio = QElapsedTimer(); self._relogio.start()

        painel = QFrame()
        painel.setObjectName("introducaoPainel")
        painel.setStyleSheet(
            f"QFrame#introducaoPainel {{ background: {tema.BEGE_CLARO};"
            f" border: 2px solid {tema.CASTANHO_MEDIO}; border-radius: 18px; }}"
        )
        titulo = QLabel("MARTELO")
        titulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        titulo.setStyleSheet(
            f"font-size: 38px; font-weight: bold; letter-spacing: 5px; color: {tema.CASTANHO_ESCURO};"
        )
        subtitulo = QLabel("Orçamentos V3")
        subtitulo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitulo.setStyleSheet(f"font-size: 21px; color: {tema.CASTANHO_MEDIO};")
        self.saudacao_label = QLabel(
            f"Bem-vindo, {nome_utilizador}." if nome_utilizador else "Bem-vindo ao Martelo V3."
        )
        self.saudacao_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.saudacao_label.setStyleSheet(f"font-size: 15px; color: {tema.TEXTO_NORMAL};")
        promessa = QLabel("Orçamentos claros · Custos controlados · Produção acompanhada")
        promessa.setAlignment(Qt.AlignmentFlag.AlignCenter)
        promessa.setStyleSheet(f"color: {tema.CINZA_ESCURO};")
        self.etapa_label = QLabel(self.ETAPAS[0])
        self.etapa_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.etapa_label.setStyleSheet(f"font-weight: bold; color: {tema.CASTANHO_ESCURO};")
        self.progresso = QProgressBar()
        self.progresso.setRange(0, 100); self.progresso.setValue(10)
        self.progresso.setTextVisible(False); self.progresso.setFixedHeight(9)
        self.progresso.setStyleSheet(
            f"QProgressBar {{ background: {tema.CINZA_CASTANHO}; border: none; border-radius: 4px; }}"
            f"QProgressBar::chunk {{ background: {tema.CASTANHO_MEDIO}; border-radius: 4px; }}"
        )
        self.ignorar_button = QPushButton("Ignorar")
        self.ignorar_button.setToolTip("Abrir imediatamente a aplicação")
        self.ignorar_button.clicked.connect(self.terminar)
        botoes = QHBoxLayout(); botoes.addStretch(); botoes.addWidget(self.ignorar_button)
        conteudo = QVBoxLayout(painel); conteudo.setContentsMargins(45, 38, 45, 28)
        conteudo.setSpacing(13); conteudo.addWidget(titulo); conteudo.addWidget(subtitulo)
        conteudo.addSpacing(8); conteudo.addWidget(self.saudacao_label); conteudo.addWidget(promessa)
        conteudo.addStretch(); conteudo.addWidget(self.etapa_label); conteudo.addWidget(self.progresso)
        conteudo.addLayout(botoes)
        layout = QVBoxLayout(self); layout.setContentsMargins(8, 8, 8, 8); layout.addWidget(painel)

        self._timer = QTimer(self); self._timer.setInterval(320)
        self._timer.timeout.connect(self._avancar); self._timer.start()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        screen = self.screen().availableGeometry()
        self.move(screen.center() - self.rect().center())

    def marcar_aplicacao_pronta(self) -> None:
        self._pronta = True
        self._indice = len(self.ETAPAS) - 1
        self.etapa_label.setText(self.ETAPAS[-1]); self.progresso.setValue(100)
        restante = max(0, 3000 - self._relogio.elapsed())
        QTimer.singleShot(restante, self.terminar)

    def _avancar(self) -> None:
        if self._pronta:
            return
        self._indice = min(self._indice + 1, len(self.ETAPAS) - 2)
        self.etapa_label.setText(self.ETAPAS[self._indice])
        self.progresso.setValue(min(85, 15 + self._indice * 28))

    def terminar(self) -> None:
        if self._terminou:
            return
        self._terminou = True; self._timer.stop(); self.concluida.emit(); self.close()
