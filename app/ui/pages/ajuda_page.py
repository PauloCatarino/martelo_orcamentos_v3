"""Página de Ajuda: em que versão estou, e já saiu uma mais recente.

Aqui viveu, durante o piloto, um centro de guias narrados pelo motor de voz do
Windows, com transcrição e uma ficha de recolha de comentários. Foi retirado em
2026-09-04: ninguém o usava, e código que ninguém usa é código que envelhece
sem se dar por isso. O que ficou é a única coisa que se consultava mesmo — o
número da versão instalada e o aviso de que há uma nova no servidor.
"""

from __future__ import annotations

import html
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.config.versao import version_completa
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho


class AjudaPage(QWidget):
    """Ajuda do Martelo: a versão instalada e a atualização."""

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)
        layout.addWidget(
            BarraCabecalho(
                "Ajuda",
                ["Versão instalada do Martelo V3 e atualizações"],
            )
        )
        layout.addWidget(self._criar_caixa_versao())
        layout.addStretch()

    # ----- Versão do Martelo -----

    def _criar_caixa_versao(self) -> QGroupBox:
        """"Que versão é que eu tenho?" e "já saiu uma correção?".

        O número da versão é a única forma de responder a "ele já tem a
        correção ou não?", e até aqui isso vivia todo na cabeça de quem instala.
        """
        caixa = QGroupBox("Versão do Martelo")
        layout = QVBoxLayout(caixa)

        self.versao_label = QLabel("A verificar…")
        self.versao_label.setWordWrap(True)
        self.versao_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.versao_label)

        self.atualizar_versao_button = QPushButton("Atualizar agora…")
        self.atualizar_versao_button.setToolTip(
            "Fecha o Martelo e abre o instalador da versão nova, que está na "
            "pasta do servidor."
        )
        self.atualizar_versao_button.clicked.connect(self._atualizar_martelo)
        self.atualizar_versao_button.setVisible(False)

        self.verificar_versao_button = QPushButton("Verificar de novo")
        self.verificar_versao_button.setToolTip(
            "Voltar a ver, na pasta do servidor, se já existe uma versão mais "
            "recente."
        )
        self.verificar_versao_button.clicked.connect(self.verificar_versao)

        linha = QHBoxLayout()
        linha.addWidget(self.atualizar_versao_button)
        linha.addWidget(self.verificar_versao_button)
        linha.addStretch()
        layout.addLayout(linha)

        # Depois de a janela existir, para o arranque não ficar preso à espera
        # do servidor quando a rede está lenta ou em baixo.
        QTimer.singleShot(0, self.verificar_versao)
        return caixa

    def verificar_versao(self) -> None:
        """Ler a pasta dos instaladores e dizer em que pé estamos."""
        from sqlalchemy.exc import SQLAlchemyError

        from app.db.session import SessionLocal
        from app.services.atualizacao_service import AtualizacaoService

        self._estado_versao = None
        try:
            with SessionLocal() as session:
                estado = AtualizacaoService(session).estado()
        except (SQLAlchemyError, OSError) as erro:
            self.versao_label.setText(
                f"Versão instalada: <b>{html.escape(version_completa())}</b><br>"
                f"<span style='color:{tema.CINZA_ESCURO};'>Não foi possível "
                f"verificar se há versão nova: {html.escape(str(erro))}</span>"
            )
            self.atualizar_versao_button.setVisible(False)
            return

        self._estado_versao = estado
        instalada = html.escape(estado.instalada)

        if estado.problema:
            self.versao_label.setText(
                f"Versão instalada: <b>{instalada}</b><br>"
                f"<span style='color:{tema.CINZA_ESCURO};'>"
                f"{html.escape(estado.problema)}</span>"
            )
            self.atualizar_versao_button.setVisible(False)
            return

        disponivel = html.escape(estado.disponivel or "")
        if estado.ha_atualizacao:
            self.versao_label.setText(
                f"Versão instalada: <b>{instalada}</b><br>"
                f"<span style='color:{tema.VERMELHO_ESCURO};'><b>Há uma versão "
                f"mais recente: {disponivel}.</b></span><br>"
                "Carregue em «Atualizar agora…» quando não estiver a meio de um "
                "orçamento."
            )
            self.atualizar_versao_button.setText(
                f"Atualizar agora para a {disponivel}…"
            )
            self.atualizar_versao_button.setVisible(True)
        else:
            self.versao_label.setText(
                f"Versão instalada: <b>{instalada}</b><br>"
                "Está atualizado — é a versão mais recente que está no servidor."
            )
            self.atualizar_versao_button.setVisible(False)

    def _atualizar_martelo(self) -> None:
        """Confirmar, abrir o instalador e fechar o Martelo."""
        estado = getattr(self, "_estado_versao", None)
        if estado is None or estado.caminho_instalador is None:
            return

        aviso = (
            f"Vai instalar a versão {estado.disponivel} por cima da "
            f"{estado.instalada}.\n\n"
            "O Martelo vai FECHAR-SE e o instalador abre a seguir. Grave o que "
            "tiver aberto antes de continuar.\n\n"
            f"Instalador:\n{estado.caminho_instalador}"
        )
        resposta = QMessageBox.question(
            self,
            "Atualizar o Martelo",
            aviso,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        try:
            # ``startfile`` abre o instalador como o Windows o abriria a partir
            # do Explorador: com o utilizador normal, e o UAC a pedir permissão
            # quando for preciso. Se o abríssemos de dentro do Martelo de outra
            # maneira, o instalador herdava o que o Martelo é — e é isso que
            # deixa o Outlook sem falar com o Martelo depois de instalar.
            os.startfile(str(estado.caminho_instalador))  # noqa: S606
        except OSError as erro:
            QMessageBox.critical(
                self,
                "Atualizar o Martelo",
                "Não foi possível abrir o instalador:\n"
                f"{estado.caminho_instalador}\n\n{erro}",
            )
            return

        QGuiApplication.quit()
