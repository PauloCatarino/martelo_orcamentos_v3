"""Faixa de miniaturas dos anexos de um ticket: colar, arrastar, escolher.

A entrada que interessa mesmo é o **Ctrl+V**: a foto do cliente chega pelo
chat, copia-se de lá e cola-se aqui. Tudo o resto é alternativa para quando a
imagem já é um ficheiro.

O widget não grava nada — junta o que o utilizador foi pondo (ficheiros
escolhidos e imagens coladas) e devolve a lista a quem sabe onde é a pasta da
obra. Assim funciona igual ao criar um ticket novo (que ainda não tem número)
e ao editar um que já existe.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QImage, QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QListWidget,
    QListWidgetItem,
    QMenu,
)

from app.domain.ocorrencia_anexos import (
    EXTENSOES_IMAGEM,
    EXTENSOES_PDF,
    e_imagem,
    e_pdf,
    existe,
)
from app.services.pdf_imagem_service import miniatura_primeira_pagina


@dataclass
class AnexoVista:
    """One thumbnail: either already saved, or waiting to be saved."""

    nome: str
    #: Preenchido quando o anexo já está na base de dados.
    anexo_id: int | None = None
    #: Ficheiro em disco (anexo gravado, ou ficheiro que o utilizador escolheu).
    caminho: str | None = None
    #: Imagem colada da área de transferência, ainda sem ficheiro.
    imagem: QImage | None = field(default=None, repr=False)

    @property
    def por_gravar(self) -> bool:
        """True while this attachment is not in the database yet."""
        return self.anexo_id is None


class FaixaAnexos(QListWidget):
    """Thumbnail strip with paste, drag-and-drop and a context menu."""

    mudou = Signal()
    aviso = Signal(str)

    def __init__(
        self,
        parent=None,
        *,
        altura: int = 104,
        tamanho_icone: QSize | None = None,
        mostrar_nomes: bool = False,
        somente_leitura: bool = False,
    ) -> None:
        super().__init__(parent)

        self._itens: list[AnexoVista] = []
        self._removidos: list[int] = []
        self._mostrar_nomes = mostrar_nomes
        self._somente_leitura = somente_leitura
        tamanho = tamanho_icone or QSize(96, 72)

        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setFlow(QListWidget.Flow.LeftToRight)
        self.setWrapping(False)
        self.setIconSize(tamanho)
        altura_texto = 24 if mostrar_nomes else 0
        self.setGridSize(
            QSize(tamanho.width() + 16, tamanho.height() + 12 + altura_texto)
        )
        self.setFixedHeight(altura)
        self.setMovement(QListWidget.Movement.Static)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(
            QListWidget.SelectionMode.SingleSelection
            if somente_leitura
            else QListWidget.SelectionMode.ExtendedSelection
        )
        self.setAcceptDrops(not somente_leitura)
        self.setDragEnabled(False)
        self.setToolTip(
            "Anexos do ticket (fotos e PDFs). Ctrl+V cola a imagem copiada do "
            "chat; também pode arrastar ficheiros para aqui. Nos PDFs a "
            "miniatura é a primeira página. Duplo-clique abre o anexo."
        )

        if not somente_leitura:
            atalho = QShortcut(QKeySequence.StandardKey.Paste, self)
            atalho.activated.connect(self.colar)

        self.itemDoubleClicked.connect(self._abrir_item)
        if not somente_leitura:
            self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            self.customContextMenuRequested.connect(self._menu_contexto)

    # ---- carregar / ler --------------------------------------------------
    def carregar(self, anexos) -> None:
        """Show the attachments a ticket already has."""
        self._itens = [
            AnexoVista(
                nome=str(getattr(anexo, "nome_original", "") or "")
                or Path(str(getattr(anexo, "caminho", ""))).name,
                anexo_id=int(getattr(anexo, "id", 0)) or None,
                caminho=str(getattr(anexo, "caminho", "") or "") or None,
            )
            for anexo in anexos or ()
        ]
        self._removidos = []
        self._render()

    def pendentes(self) -> list[AnexoVista]:
        """Attachments chosen or pasted that still need saving."""
        return [item for item in self._itens if item.por_gravar]

    def removidos(self) -> list[int]:
        """Ids of saved attachments the user took out."""
        return list(self._removidos)

    def total(self) -> int:
        """How many thumbnails are on screen."""
        return len(self._itens)

    # ---- acrescentar -----------------------------------------------------
    def colar(self) -> None:
        """Take whatever is on the clipboard: an image or copied files."""
        if self._somente_leitura:
            return
        dados = QApplication.clipboard().mimeData()
        if dados is None:
            return

        if dados.hasImage():
            imagem = QApplication.clipboard().image()
            if not imagem.isNull():
                self._acrescentar_imagem(imagem)
                return

        if dados.hasUrls():
            caminhos = [
                url.toLocalFile() for url in dados.urls() if url.isLocalFile()
            ]
            if caminhos:
                self.acrescentar_ficheiros(caminhos)
                return

        self.aviso.emit("Não há nenhuma imagem nem ficheiro copiado.")

    def escolher_ficheiros(self) -> None:
        """Open the file chooser for pictures and PDFs."""
        imagens = " ".join(f"*{ext}" for ext in sorted(EXTENSOES_IMAGEM))
        pdfs = " ".join(f"*{ext}" for ext in sorted(EXTENSOES_PDF))
        caminhos, _ = QFileDialog.getOpenFileNames(
            self,
            "Escolher anexos do ticket",
            "",
            f"Fotos e PDFs ({imagens} {pdfs});;Imagens ({imagens});;"
            f"PDF ({pdfs});;Todos os ficheiros (*.*)",
        )
        if caminhos:
            self.acrescentar_ficheiros(caminhos)

    def acrescentar_ficheiros(self, caminhos) -> None:
        """Add files chosen or dropped by the user."""
        if self._somente_leitura:
            return
        novos = 0
        for caminho in caminhos or ():
            texto = str(caminho or "").strip()
            if not texto or not existe(texto):
                continue
            self._itens.append(AnexoVista(nome=Path(texto).name, caminho=texto))
            novos += 1

        if novos:
            self._render()
            self.mudou.emit()
        else:
            self.aviso.emit("Nenhum dos ficheiros foi encontrado.")

    def _acrescentar_imagem(self, imagem: QImage) -> None:
        nome = f"colada_{len(self._itens) + 1:02d}.png"
        self._itens.append(AnexoVista(nome=nome, imagem=imagem))
        self._render()
        self.mudou.emit()

    # ---- remover ---------------------------------------------------------
    def remover_selecionados(self) -> None:
        """Take the selected thumbnails out of the ticket."""
        if self._somente_leitura:
            return
        linhas = sorted((self.row(item) for item in self.selectedItems()), reverse=True)
        if not linhas:
            return

        for linha in linhas:
            if 0 <= linha < len(self._itens):
                anexo = self._itens.pop(linha)
                if anexo.anexo_id is not None:
                    self._removidos.append(anexo.anexo_id)

        self._render()
        self.mudou.emit()

    # ---- eventos ---------------------------------------------------------
    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt)
        if not self._somente_leitura and event.key() in (
            Qt.Key.Key_Delete,
            Qt.Key.Key_Backspace,
        ):
            self.remover_selecionados()
            return
        super().keyPressEvent(event)

    def dragEnterEvent(self, event) -> None:  # noqa: N802 (Qt)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:  # noqa: N802 (Qt)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:  # noqa: N802 (Qt)
        if not event.mimeData().hasUrls():
            super().dropEvent(event)
            return
        caminhos = [
            url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()
        ]
        self.acrescentar_ficheiros(caminhos)
        event.acceptProposedAction()

    # ---- apresentação ----------------------------------------------------
    def _render(self) -> None:
        self.clear()
        for anexo in self._itens:
            item = QListWidgetItem()
            item.setIcon(self._icone(anexo))
            if self._mostrar_nomes:
                item.setText(anexo.nome)
                item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
            item.setToolTip(self._tooltip(anexo))
            item.setSizeHint(self.gridSize())
            self.addItem(item)

    def _icone(self, anexo: AnexoVista):
        if anexo.imagem is not None:
            return QPixmap.fromImage(anexo.imagem).scaled(
                self.iconSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        if anexo.caminho and e_imagem(anexo.caminho) and existe(anexo.caminho):
            return QPixmap(anexo.caminho).scaled(
                self.iconSize(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        if anexo.caminho and e_pdf(anexo.caminho) and existe(anexo.caminho):
            # Um PDF vê-se como as fotos: a primeira página faz de miniatura.
            miniatura = miniatura_primeira_pagina(
                anexo.caminho, self.iconSize().width(), self.iconSize().height()
            )
            if miniatura is not None and not miniatura.isNull():
                return miniatura
        return QPixmap()

    @staticmethod
    def _tooltip(anexo: AnexoVista) -> str:
        if anexo.imagem is not None:
            return f"{anexo.nome} (colada — grava ao registar o ticket)"
        if anexo.caminho and not existe(anexo.caminho):
            return f"{anexo.nome}\n{anexo.caminho}\n(ficheiro já não está lá)"
        abrir = (
            "PDF — duplo-clique abre"
            if e_pdf(anexo.caminho)
            else "Duplo-clique abre"
        )
        return f"{anexo.nome}\n{anexo.caminho or ''}\n({abrir})"

    def _abrir_item(self, item: QListWidgetItem) -> None:
        linha = self.row(item)
        if not (0 <= linha < len(self._itens)):
            return
        anexo = self._itens[linha]
        if not anexo.caminho or not existe(anexo.caminho):
            self.aviso.emit("Este anexo ainda não foi gravado.")
            return

        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(anexo.caminho))

    def _menu_contexto(self, posicao) -> None:
        menu = QMenu(self)
        colar = menu.addAction("Colar imagem (Ctrl+V)")
        escolher = menu.addAction("Escolher fotos ou PDFs…")
        menu.addSeparator()
        remover = menu.addAction("Remover selecionados")
        remover.setEnabled(bool(self.selectedItems()))

        escolhida = menu.exec(self.mapToGlobal(posicao))
        if escolhida == colar:
            self.colar()
        elif escolhida == escolher:
            self.escolher_ficheiros()
        elif escolhida == remover:
            self.remover_selecionados()
