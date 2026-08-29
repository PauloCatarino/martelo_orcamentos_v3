"""Uma tabela com um título que se abre, se fecha e se põe em grande.

Feito para a Pesquisa IA, onde quatro tabelas empilhadas ocupavam o ecrã todo
e nenhuma se via bem — e as vazias ocupavam tanto espaço como as cheias. O
título passa a dizer quantos resultados há antes de se abrir seja o que for, e
o botão ⤢ dá uma tabela de cada vez em ecrã inteiro.

Não sabe nada da Pesquisa IA: recebe um título e um widget qualquer.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.ui import tema

#: O que o Qt entende por "sem limite de altura".
ALTURA_LIVRE = 16777215

TEXTO_GRANDE = "Em grande"
TEXTO_VOLTAR = "Voltar"

_ESTILO_CABECA = (
    "QPushButton {"
    f" background-color: {tema.CASTANHO_MEDIO}; color: #FFFFFF;"
    " border: none; padding: 7px 10px; font-weight: bold; text-align: left; }"
    f"QPushButton:hover {{ background-color: {tema.CASTANHO_ESCURO}; }}"
)

_ESTILO_CONTA = (
    "QLabel {"
    f" background-color: {tema.CASTANHO_MEDIO}; color: #F3E9DC;"
    " padding: 7px 10px; font-weight: bold; }"
)

_ESTILO_BOTAO_GRANDE = (
    "QPushButton {"
    f" background-color: {tema.CASTANHO_MEDIO}; color: #FFFFFF;"
    " border: none; padding: 7px 10px; font-weight: bold; }"
    f"QPushButton:hover {{ background-color: {tema.CASTANHO_ESCURO}; }}"
)

_ESTILO_VAZIO = f"QLabel {{ color: {tema.CINZA_ESCURO}; padding: 14px 12px; }}"


class PainelRecolhivel(QWidget):
    """Título clicável + conteúdo que se esconde.

    ``grande_pedido`` é emitido quando alguém carrega no ⤢; quem monta a
    página é que decide o que fazer com os outros painéis — este não conhece
    os irmãos.
    """

    aberto_mudou = Signal(bool)
    grande_pedido = Signal(object)

    def __init__(
        self,
        titulo: str,
        conteudo: QWidget,
        *,
        aberto: bool = True,
        com_botao_grande: bool = True,
    ) -> None:
        super().__init__()
        self._titulo = titulo
        self._conteudo = conteudo
        self._em_grande = False
        self._aberto = bool(aberto)
        # Uma tabela vazia fecha-se sozinha; se a pessoa a abrir a` mao, fica
        # aberta, e por isso e' preciso saber quem a fechou.
        self._fechado_por_estar_vazio = False

        self.botao_titulo = QPushButton()
        self.botao_titulo.setStyleSheet(_ESTILO_CABECA)
        self.botao_titulo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.botao_titulo.clicked.connect(self._alternar)
        self.botao_titulo.setToolTip("Clique para abrir ou fechar esta tabela.")

        self.label_conta = QLabel("")
        self.label_conta.setStyleSheet(_ESTILO_CONTA)
        self.label_conta.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        cabeca = QHBoxLayout()
        cabeca.setContentsMargins(0, 0, 0, 0)
        cabeca.setSpacing(0)
        cabeca.addWidget(self.botao_titulo, stretch=1)
        cabeca.addWidget(self.label_conta)

        self.botao_grande: QPushButton | None = None
        if com_botao_grande:
            # Texto e nao um simbolo: as setas de "maximizar" (⤢) nem sempre
            # existem nas fontes do Windows e sairiam quadrados. E quem usa
            # isto le' "Em grande" sem ter de adivinhar o desenho.
            self.botao_grande = QPushButton(TEXTO_GRANDE)
            self.botao_grande.setStyleSheet(_ESTILO_BOTAO_GRANDE)
            self.botao_grande.setCursor(Qt.CursorShape.PointingHandCursor)
            self.botao_grande.setToolTip(
                "Ver so' esta tabela, em grande. Carregue outra vez para voltar."
            )
            self.botao_grande.clicked.connect(lambda: self.grande_pedido.emit(self))
            cabeca.addWidget(self.botao_grande)

        self.label_vazio = QLabel("")
        self.label_vazio.setStyleSheet(_ESTILO_VAZIO)
        self.label_vazio.setWordWrap(True)
        self.label_vazio.hide()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(cabeca)
        layout.addWidget(self.label_vazio)
        layout.addWidget(conteudo, stretch=1)

        self._escrever_titulo()
        self.abrir(aberto)

    # ------------------------------------------------------------- abrir --

    def esta_aberto(self) -> bool:
        # Guardado a` parte, e nao lido do `isVisible()`: enquanto a pagina nao
        # for mostrada no ecra' o Qt diz que nada esta' visivel, e os paineis
        # nasciam todos "fechados" sem ninguem os ter fechado.
        return self._aberto

    def abrir(self, aberto: bool) -> None:
        self._aberto = bool(aberto)
        vazio = bool(self.label_vazio.text())
        self._conteudo.setVisible(aberto and not vazio)
        self.label_vazio.setVisible(aberto and vazio)
        # Fechado, o painel nao pode roubar espaco ao splitter: fica so' com a
        # altura da barra do titulo.
        self.setMaximumHeight(
            ALTURA_LIVRE if aberto else self.botao_titulo.sizeHint().height()
        )
        self._escrever_titulo()
        self.aberto_mudou.emit(aberto)

    def _alternar(self) -> None:
        self._fechado_por_estar_vazio = False
        self.abrir(not self.esta_aberto())

    # ------------------------------------------------------------ grande --

    def em_grande(self) -> bool:
        return self._em_grande

    def definir_em_grande(self, valor: bool) -> None:
        self._em_grande = bool(valor)
        self._escrever_titulo()

    # ------------------------------------------------------- o que mostra --

    def definir_contagem(
        self,
        mostrados: int,
        total: int | None = None,
        *,
        detalhe: str = "",
        texto_vazio: str = "",
    ) -> None:
        """Quantos resultados tem, e o que dizer quando nao tem nenhum."""
        if total is None or total == mostrados:
            conta = str(mostrados)
        else:
            conta = f"{mostrados} de {total}"
        if detalhe:
            conta = f"{conta} · {detalhe}"
        self.label_conta.setText(conta)

        self.label_vazio.setText(texto_vazio if mostrados == 0 else "")

        if mostrados == 0:
            # Uma tabela vazia a ocupar meio ecra' e' o que tornava esta pagina
            # confusa: fecha-se sozinha e diz porque' esta' vazia.
            if self.esta_aberto():
                self._fechado_por_estar_vazio = True
                self.abrir(False)
        elif self._fechado_por_estar_vazio:
            self._fechado_por_estar_vazio = False
            self.abrir(True)
        else:
            self.abrir(self.esta_aberto())

    def _escrever_titulo(self) -> None:
        seta = "▼" if self.esta_aberto() else "▶"
        self.botao_titulo.setText(f"{seta}  {self._titulo}")
        if self.botao_grande is not None:
            self.botao_grande.setText(
                TEXTO_VOLTAR if self._em_grande else TEXTO_GRANDE
            )
