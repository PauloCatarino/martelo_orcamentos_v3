"""Página de Ajuda: em que versão estou, e já saiu uma mais recente.

Aqui viveu, durante o piloto, um centro de guias narrados pelo motor de voz do
Windows, com transcrição e uma ficha de recolha de comentários. Foi retirado em
2026-09-04: ninguém o usava, e código que ninguém usa é código que envelhece
sem se dar por isso. O que ficou é a única coisa que se consultava mesmo — o
número da versão instalada e o aviso de que há uma nova no servidor.
"""

from __future__ import annotations

import html
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QDesktopServices
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
from app.ui.helpers.aviso_atualizacao import instalar_e_fechar
from app.ui.helpers.novidades_versao import abrir_novidades, botao_ver_novidades
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
        layout.addWidget(self._criar_caixa_novidades())
        layout.addStretch()
        # Linha de estado («supervisor»), como em todos os menus.
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color:{tema.CINZA_ESCURO};")
        layout.addWidget(self.status_label)

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

    # ----- Novidades das versões -----

    def _criar_caixa_novidades(self) -> QGroupBox:
        """O que mudou em cada versão, e onde estão os instaladores (19-11-2026).

        As novidades são HTML/PDF na subpasta ``Novidades`` da pasta dos
        instaladores; cada alteração começa pela área (Orçamentos, Produção, Geral).
        """
        caixa = QGroupBox("Novidades das versões")
        layout = QVBoxLayout(caixa)

        self.pasta_label = QLabel("A verificar…")
        self.pasta_label.setWordWrap(True)
        self.pasta_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        layout.addWidget(self.pasta_label)

        self.novidades_label = QLabel("")
        self.novidades_label.setWordWrap(True)
        self.novidades_label.setOpenExternalLinks(False)
        self.novidades_label.linkActivated.connect(self._abrir_link)
        self.novidades_label.setToolTip(
            "Clique numa versão para abrir as novidades no navegador (HTML) ou o PDF"
        )
        layout.addWidget(self.novidades_label)

        self.ver_novidades_button = QPushButton("Novidades desta versão")
        self.ver_novidades_button.setToolTip(
            "Abrir no navegador o que mudou na versão que está instalada neste PC"
        )
        self.ver_novidades_button.clicked.connect(self._ver_novidades_instalada)
        self.abrir_pasta_button = QPushButton("Abrir a pasta das atualizações")
        self.abrir_pasta_button.setToolTip(
            "Abrir no Explorador a pasta do servidor com os instaladores e as novidades"
        )
        self.abrir_pasta_button.clicked.connect(self._abrir_pasta)

        linha = QHBoxLayout()
        linha.addWidget(self.ver_novidades_button)
        linha.addWidget(self.abrir_pasta_button)
        linha.addStretch()
        layout.addLayout(linha)

        self._pasta_instaladores: Path | None = None
        self._novidades: list = []
        QTimer.singleShot(0, self.ler_novidades)
        return caixa

    def ler_novidades(self) -> None:
        """Ler a pasta dos instaladores e listar as novidades que lá estão."""
        from sqlalchemy.exc import SQLAlchemyError

        from app.db.session import SessionLocal
        from app.services.atualizacao_service import AtualizacaoService, listar_novidades

        try:
            with SessionLocal() as session:
                pasta = AtualizacaoService(session).pasta()
            novidades = listar_novidades(pasta) if pasta else []
        except (SQLAlchemyError, OSError) as erro:
            self.pasta_label.setText(
                f"Não foi possível ver a pasta das atualizações: {html.escape(str(erro))}"
            )
            self.ver_novidades_button.setEnabled(False)
            self.abrir_pasta_button.setEnabled(False)
            return

        self._pasta_instaladores = pasta
        self._novidades = novidades
        if pasta is None:
            self.pasta_label.setText(
                "A pasta dos instaladores ainda não está definida "
                "(Configurações → Caminhos do Sistema)."
            )
        else:
            self.pasta_label.setText(
                f"Pasta das atualizações (instaladores e novidades):<br><b>{html.escape(str(pasta))}</b>"
            )
        self.abrir_pasta_button.setEnabled(pasta is not None)

        if not novidades:
            self.novidades_label.setText("Ainda não há novidades na pasta.")
        else:
            linhas = []
            for indice, n in enumerate(novidades[:8]):
                pdf = f" · <a href='p:{indice}'>PDF</a>" if n.pdf else ""
                linhas.append(
                    f"Versão <a href='h:{indice}'><b>{html.escape(n.versao)}</b></a>{pdf}"
                )
            self.novidades_label.setText(
                "Novidades (cada alteração começa pela área — Orçamentos, Produção ou "
                "Geral):<br>" + "<br>".join(linhas)
            )
        instalada = version_completa()
        tem = any(n.versao == instalada for n in novidades)
        self.ver_novidades_button.setEnabled(tem)
        self.ver_novidades_button.setText(f"Novidades desta versão ({instalada})")
        if not tem:
            self.ver_novidades_button.setToolTip(
                f"Ainda não há novidades da {instalada} na pasta das atualizações"
            )

    def _abrir_link(self, link: str) -> None:
        tipo, _, indice = link.partition(":")
        try:
            novidades = self._novidades[int(indice)]
        except (ValueError, IndexError):
            return
        caminho = novidades.pdf if tipo == "p" else novidades.html
        if abrir_novidades(self, caminho):
            self.status_label.setText(f"Abertas as novidades da {novidades.versao}.")

    def _ver_novidades_instalada(self) -> None:
        instalada = version_completa()
        novidades = next((n for n in self._novidades if n.versao == instalada), None)
        if novidades is not None and abrir_novidades(self, novidades.html):
            self.status_label.setText(f"Abertas as novidades da {instalada}.")

    def _abrir_pasta(self) -> None:
        pasta = self._pasta_instaladores
        if pasta is None:
            return
        if QDesktopServices.openUrl(QUrl.fromLocalFile(str(pasta))):
            self.status_label.setText("Aberta a pasta das atualizações.")
        else:
            QMessageBox.warning(
                self, "Pasta das atualizações",
                f"Não foi possível abrir a pasta:\n{pasta}\n\nVerifique a ligação ao servidor.",
            )

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
        caixa = QMessageBox(self)
        caixa.setIcon(QMessageBox.Icon.Question)
        caixa.setWindowTitle("Atualizar o Martelo")
        caixa.setText(aviso)
        # 19-11-2026: ver o que muda antes de instalar.
        novidades = botao_ver_novidades(
            caixa, estado.disponivel, estado.novidades_disponivel
        )
        sim = caixa.addButton("Instalar", QMessageBox.ButtonRole.YesRole)
        sim.setToolTip("Fechar o Martelo e abrir o instalador da versão nova")
        nao = caixa.addButton("Cancelar", QMessageBox.ButtonRole.NoRole)
        nao.setToolTip("Não instalar agora")
        caixa.setDefaultButton(nao)
        caixa.setEscapeButton(nao)
        while True:
            caixa.exec()
            if novidades is not None and caixa.clickedButton() is novidades:
                abrir_novidades(self, estado.novidades_disponivel)
                continue
            break
        if caixa.clickedButton() is not sim:
            return

        # A mesma passagem que o aviso da manhã: antes de fechar, todos os
        # menus perguntam se há alterações por gravar — não só o que está à
        # frente (aqui, a própria Ajuda, que não tem nada para gravar).
        instalar_e_fechar(
            self,
            estado,
            pode_fechar=getattr(self.window(), "pode_fechar_tudo", None),
        )
