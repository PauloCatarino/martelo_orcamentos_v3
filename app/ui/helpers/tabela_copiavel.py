"""Copiar o que se vê numa tabela só de leitura: Ctrl+C, botão direito e visor.

Pedido do Paulo (10-10-2026) na Pesquisa IA: selecionar um pedaço de texto e
levá-lo para outro sítio com Ctrl+C. Numa tabela só de leitura isso não era
possível: as linhas inteiras ficavam selecionadas, o Ctrl+C levava só a célula
onde se tinha clicado (sem se ver qual) e não havia maneira de apanhar só uma
parte de uma descrição.

Aqui fica, para qualquer tabela:

* seleciona-se célula a célula, como no Excel (arrastar ou Shift/Ctrl+clique);
* Ctrl+C copia exatamente o que está selecionado — uma célula sai como texto
  simples; várias saem separadas por tabulações, prontas para colar no Excel;
* o botão direito tem «Copiar», «Copiar a linha inteira» e «Copiar a tabela
  toda (com títulos)»;
* o visor (:class:`VisorCelula`) mostra o texto completo da célula escolhida
  num campo onde se pode selecionar só uma parte, como a barra de fórmulas do
  Excel.

Não sabe nada da Pesquisa IA: recebe uma ``QTableWidget`` qualquer.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QGuiApplication, QKeySequence
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLineEdit,
    QMenu,
    QTableWidget,
)

from app.ui import tema

TEXTO_COPIAR = "Copiar"
TEXTO_COPIAR_LINHA = "Copiar a linha inteira"
TEXTO_COPIAR_TABELA = "Copiar a tabela toda (com títulos)"

DICA_TABELA = (
    "Ctrl+C copia as células selecionadas (arraste ou use Shift/Ctrl+clique "
    "para escolher várias). Botão direito para copiar a linha inteira ou a "
    "tabela toda."
)


def _limpo(texto: str) -> str:
    """Uma célula numa só linha: tabulações e mudanças de linha partiam o Excel."""
    partes = re.split(r"[\t\r\n]+", texto or "")
    return " ".join(parte.strip() for parte in partes if parte.strip()) if len(partes) > 1 else (texto or "")


def _texto(tabela: QTableWidget, linha: int, coluna: int) -> str:
    item = tabela.item(linha, coluna)
    return item.text() if item is not None else ""


def _colunas_visiveis(tabela: QTableWidget) -> list[int]:
    """As colunas à vista, pela ordem em que aparecem no ecrã."""
    cabecalho = tabela.horizontalHeader()
    colunas = [c for c in range(tabela.columnCount()) if not tabela.isColumnHidden(c)]
    return sorted(colunas, key=cabecalho.visualIndex)


def _linhas_visiveis(tabela: QTableWidget, linhas) -> list[int]:
    cabecalho = tabela.verticalHeader()
    visiveis = [l for l in set(linhas) if not tabela.isRowHidden(l)]
    return sorted(visiveis, key=cabecalho.visualIndex)


def texto_da_selecao(tabela: QTableWidget) -> str:
    """O que está selecionado, em texto: células por tabulações, linhas por ``\\n``.

    Uma seleção salteada (Ctrl+clique) sai num retângulo com as células que
    não foram escolhidas em branco — é o que o Excel espera ao colar.
    """
    selecionadas = {
        (indice.row(), indice.column()) for indice in tabela.selectedIndexes()
    }
    if not selecionadas:
        atual = tabela.currentItem()
        return atual.text() if atual is not None else ""
    ordem = {c: i for i, c in enumerate(_colunas_visiveis(tabela))}
    colunas = sorted(
        {c for _l, c in selecionadas if c in ordem}, key=ordem.__getitem__
    )
    linhas = _linhas_visiveis(tabela, (l for l, _c in selecionadas))
    if len(linhas) == 1 and len(colunas) == 1:
        return _texto(tabela, linhas[0], colunas[0])
    return "\n".join(
        "\t".join(
            _limpo(_texto(tabela, linha, coluna)) if (linha, coluna) in selecionadas else ""
            for coluna in colunas
        )
        for linha in linhas
    )


def texto_das_linhas(
    tabela: QTableWidget, linhas, *, com_titulos: bool = False
) -> str:
    """Linhas inteiras (todas as colunas à vista), opcionalmente com os títulos."""
    colunas = _colunas_visiveis(tabela)
    partes: list[str] = []
    if com_titulos:
        titulos = []
        for coluna in colunas:
            cabeca = tabela.horizontalHeaderItem(coluna)
            titulos.append(_limpo(cabeca.text()) if cabeca is not None else "")
        partes.append("\t".join(titulos))
    for linha in _linhas_visiveis(tabela, linhas):
        partes.append(
            "\t".join(_limpo(_texto(tabela, linha, coluna)) for coluna in colunas)
        )
    return "\n".join(partes)


def _para_a_area_de_transferencia(texto: str) -> bool:
    if not texto:
        return False
    QGuiApplication.clipboard().setText(texto)
    return True


def copiar_selecao(tabela: QTableWidget) -> bool:
    """Ctrl+C: põe a seleção na área de transferência. ``False`` se não havia nada."""
    return _para_a_area_de_transferencia(texto_da_selecao(tabela))


def copiar_linhas_selecionadas(tabela: QTableWidget) -> bool:
    linhas = {indice.row() for indice in tabela.selectedIndexes()}
    if not linhas and tabela.currentRow() >= 0:
        linhas = {tabela.currentRow()}
    return _para_a_area_de_transferencia(texto_das_linhas(tabela, linhas))


def copiar_tabela(tabela: QTableWidget) -> bool:
    return _para_a_area_de_transferencia(
        texto_das_linhas(tabela, range(tabela.rowCount()), com_titulos=True)
    )


class _AtalhoCopiar(QObject):
    """Apanha o Ctrl+C antes da tabela (que só copiaria a célula atual)."""

    def __init__(self, tabela: QTableWidget) -> None:
        super().__init__(tabela)
        self._tabela = tabela

    def eventFilter(self, objeto, evento):  # noqa: N802 - nome do Qt
        tipo = evento.type()
        if tipo in (QEvent.Type.KeyPress, QEvent.Type.ShortcutOverride):
            if evento.matches(QKeySequence.StandardKey.Copy):
                if tipo == QEvent.Type.ShortcutOverride:
                    # Fica com a tecla: nenhum atalho da janela a rouba.
                    evento.accept()
                    return True
                copiar_selecao(self._tabela)
                return True
        return super().eventFilter(objeto, evento)


def _menu_de_copia(tabela: QTableWidget, posicao) -> None:
    menu = QMenu(tabela)
    acao = menu.addAction(TEXTO_COPIAR, lambda: copiar_selecao(tabela))
    acao.setShortcut(QKeySequence(QKeySequence.StandardKey.Copy))
    menu.addAction(TEXTO_COPIAR_LINHA, lambda: copiar_linhas_selecionadas(tabela))
    menu.addAction(TEXTO_COPIAR_TABELA, lambda: copiar_tabela(tabela))
    vazia = tabela.rowCount() == 0
    for acao in menu.actions():
        acao.setEnabled(not vazia)
    menu.exec(tabela.viewport().mapToGlobal(posicao))


def tornar_copiavel(tabela: QTableWidget) -> QTableWidget:
    """Seleção célula a célula, Ctrl+C e menu do botão direito para copiar."""
    tabela.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
    tabela.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    filtro = _AtalhoCopiar(tabela)
    tabela.installEventFilter(filtro)
    tabela._filtro_copiar = filtro  # vive enquanto a tabela viver
    tabela.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    tabela.customContextMenuRequested.connect(
        lambda posicao: _menu_de_copia(tabela, posicao)
    )
    return tabela


class VisorCelula(QLineEdit):
    """O texto completo da célula escolhida, para selecionar só uma parte.

    Como a barra de fórmulas do Excel: clica-se numa célula, o texto aparece
    aqui inteiro (mesmo o que na tabela está cortado) e pode-se arrastar o rato
    sobre a parte que interessa e carregar em Ctrl+C. É só de leitura: mudar o
    texto aqui não mudaria nada na origem.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setReadOnly(True)
        self.setObjectName("visorCelula")
        self.setStyleSheet(f"QLineEdit#visorCelula {{ {tema.ESTILO_CAMPO_BLOQUEADO} padding: 3px 6px; }}")
        self.setPlaceholderText(
            "Clique numa célula: o texto completo aparece aqui para selecionar "
            "só uma parte e copiar com Ctrl+C."
        )
        self.setToolTip(
            "Texto completo da célula escolhida. Selecione a parte que quer "
            "(arrastar com o rato ou Shift+setas) e carregue em Ctrl+C.\n"
            "É só de leitura: os resultados vêm do V3, do PHC e dos "
            "catálogos e não se alteram aqui."
        )

    def mostrar(self, texto: str) -> None:
        self.setText(texto or "")
        self.setCursorPosition(0)

    def acompanhar(self, tabela: QTableWidget) -> None:
        """Passa a mostrar a célula atual desta tabela."""

        def _atual(linha: int, coluna: int, *_anteriores) -> None:
            if linha < 0 or coluna < 0:
                self.mostrar("")
                return
            self.mostrar(_texto(tabela, linha, coluna))

        tabela.currentCellChanged.connect(_atual)
        tabela.cellClicked.connect(_atual)

    def mostrar_atual_de(self, tabela: QTableWidget | None) -> None:
        """Ao mudar de separador, o visor passa para a célula dessa tabela."""
        item = tabela.currentItem() if tabela is not None else None
        self.mostrar(item.text() if item is not None else "")
