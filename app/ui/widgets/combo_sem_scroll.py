"""Campos que nunca mudam de valor só porque a roda do rato lhes passou por cima.

Dentro de uma tabela grande — ou de um diálogo com muitos campos que se rola —
o rato passa por cima de dezenas de células enquanto se procura a linha certa.
Um ``QComboBox``/``QSpinBox`` normal apanha essa roda e muda de valor sem
ninguém dar por isso. No custeio, isso trocava o material da peça e mexia no
preço do orçamento em silêncio, que foi o que o Paulo reportou em 2026-09-04.

A regra é a mesma em todos: **a roda só conta depois de o campo estar mesmo a
ser usado** (a lista aberta, no caso dos dropdowns; o foco no campo, nos
restantes). Fora disso o evento é devolvido ao pai, para a tabela ou o diálogo
rolarem como o utilizador espera. As setas, o teclado e a escrita direta
continuam todos a funcionar.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QSortFilterProxyModel, Qt, QTimer
from PySide6.QtWidgets import QComboBox, QCompleter, QDateEdit, QDoubleSpinBox, QSpinBox

from app.domain.pesquisa_texto import normalizar


class _SemRodaSemFoco:
    """Mixin: a roda só mexe no valor quando o campo tem o foco."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Sem foco pela roda: só clique ou teclado põem o campo em foco.
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self.hasFocus():
            super().wheelEvent(event)
            return

        event.ignore()


class ComboSemScroll(QComboBox):
    """Dropdown que só responde à roda com a lista aberta."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def wheelEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Only consume the wheel while the popup is open; otherwise scroll the table."""
        if self.view().isVisible():
            super().wheelEvent(event)
            return

        event.ignore()


def _compacto(texto: object) -> str:
    """Sem acentos, maiúsculas, pontuação nem espaços: «MÓVEIS J.F.» -> «moveisjf»."""
    return normalizar(texto).replace(" ", "")


class _FiltroSemAcentos(QSortFilterProxyModel):
    """Deixa passar as opções que contêm cada palavra escrita, sem olhar a acentos."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._termos: tuple[str, ...] = ()

    def definir(self, texto: str) -> None:
        termos = tuple(normalizar(texto).split())
        if termos == self._termos:
            return
        self.beginFilterChange()
        self._termos = termos
        self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

    def filterAcceptsRow(self, linha, pai) -> bool:  # noqa: N802 (Qt naming)
        if not self._termos:
            return True
        opcao = _compacto(self.sourceModel().index(linha, 0, pai).data())
        return all(termo in opcao for termo in self._termos)


class ComboPesquisavel(ComboSemScroll):
    """Dropdown de filtro onde também se escreve: as sugestões encolhem ao que se escreve.

    Pedido do Paulo (01-10-2026) para o filtro «Cliente» dos Orçamentos,
    Produção, Ponto Situação e Início: com centenas de clientes, encontrar um
    na lista obrigava a rolar a barra. Escrever «jf viva» sugere «MÓVEIS J.F.
    VIVA» — acentos, maiúsculas e pontuação não contam.

    O filtro só muda quando se ESCOLHE uma opção (clique na sugestão, Enter, ou
    sair do campo com um nome que só tem uma sugestão); a meio da escrita a
    lista de obras não mexe. Por isso quem usa este campo liga-se ao
    ``currentIndexChanged``: num campo editável o ``currentTextChanged`` dispara
    a cada tecla. Pela mesma razão ``currentText()`` devolve a opção escolhida
    e não o que está a meio de ser escrito.
    """

    DICA = (
        "Escreva parte do nome para o encontrar (acentos e maiúsculas não contam) "
        "e escolha na lista que aparece, ou carregue Enter. A seta mostra a lista toda."
    )

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.setToolTip(self.DICA)
        self._filtro = _FiltroSemAcentos(self)
        self._filtro.setSourceModel(self.model())
        sugestoes = QCompleter(self._filtro, self)
        sugestoes.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
        sugestoes.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        sugestoes.setMaxVisibleItems(15)
        self.setCompleter(sugestoes)
        sugestoes.activated[str].connect(self._escolher_texto)
        campo = self.lineEdit()
        campo.setPlaceholderText("Escreva para procurar…")
        campo.textEdited.connect(self._ao_escrever)
        campo.editingFinished.connect(self._confirmar)
        campo.installEventFilter(self)

    # ---- o que as páginas leem ---------------------------------------------
    def currentText(self) -> str:  # noqa: N802 (Qt naming)
        """A opção escolhida; o que está a meio de ser escrito não conta."""
        linha = self.currentIndex()
        return self.itemText(linha) if linha >= 0 else ""

    def setCurrentText(self, texto: str) -> None:  # noqa: N802 (Qt naming)
        """Escolher pelo nome, como num dropdown normal (sem igual, nada muda)."""
        linha = self.findText(texto)
        if linha < 0:
            linha = self._linha_igual(texto)
        if linha is not None and linha >= 0:
            self.setCurrentIndex(linha)

    # ---- escrita -------------------------------------------------------------
    def _ao_escrever(self, texto: str) -> None:
        self._filtro.definir(texto)
        if texto.strip():
            self.completer().complete()
        else:
            self.completer().popup().hide()

    def _escolher_texto(self, texto: str) -> None:
        linha = self.findText(texto)
        if linha >= 0 and linha != self.currentIndex():
            self.setCurrentIndex(linha)
        # Depois de o QCompleter acabar de escrever a sugestão no campo.
        QTimer.singleShot(0, self._repor_texto)

    def _confirmar(self) -> None:
        """Enter ou saída do campo: escolhe a opção certa ou volta à que estava."""
        texto = self.lineEdit().text()
        linha = self._linha_para(texto)
        if linha is None and self.lineEdit().hasFocus() and self._candidatas(texto):
            # Enter com várias sugestões: reabre a lista para escolher uma.
            self._ao_escrever(texto)
            return
        if linha is not None and linha != self.currentIndex():
            self.setCurrentIndex(linha)
        self._repor_texto()

    def _linha_igual(self, texto: str) -> int | None:
        alvo = _compacto(texto)
        for linha in range(self.count()):
            if _compacto(self.itemText(linha)) == alvo:
                return linha
        return None

    def _linha_para(self, texto: str) -> int | None:
        """Vazio = a primeira opção («Todos»); igual ou uma só sugestão = essa."""
        if not normalizar(texto):
            return 0 if self.count() else None
        linha = self._linha_igual(texto)
        if linha is not None:
            return linha
        candidatas = self._candidatas(texto)
        return candidatas[0] if len(candidatas) == 1 else None

    def _candidatas(self, texto: str) -> list[int]:
        termos = normalizar(texto).split()
        return [
            linha
            for linha in range(self.count())
            if all(termo in _compacto(self.itemText(linha)) for termo in termos)
        ]

    def _repor_texto(self) -> None:
        linha = self.currentIndex()
        texto = self.itemText(linha) if linha >= 0 else ""
        if self.lineEdit().text() != texto:
            self.lineEdit().setText(texto)

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 (Qt naming)
        if objeto is self.lineEdit():
            if evento.type() == QEvent.Type.FocusIn:
                # Ao clicar, fica tudo selecionado: escrever substitui o «Todos».
                QTimer.singleShot(0, self.lineEdit().selectAll)
            elif (
                evento.type() == QEvent.Type.KeyPress
                and evento.key() == Qt.Key.Key_Escape
                and not self.completer().popup().isVisible()
            ):
                self._repor_texto()
                self.lineEdit().selectAll()
                return True
        return super().eventFilter(objeto, evento)


class SpinSemScroll(_SemRodaSemFoco, QSpinBox):
    """Campo de número inteiro que só responde à roda quando tem o foco."""


class SpinDuploSemScroll(_SemRodaSemFoco, QDoubleSpinBox):
    """Campo de número decimal que só responde à roda quando tem o foco."""


class DataSemScroll(_SemRodaSemFoco, QDateEdit):
    """Campo de data que só responde à roda quando tem o foco."""
