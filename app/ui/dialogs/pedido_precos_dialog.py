"""Dialog to ask suppliers for updated prices."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QMessageBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.domain.materia_prima_types import MESES_PRECO_DESATUALIZADO
from app.domain.pedido_precos import PedidoFornecedor
from app.ui import tema
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class PedidoPrecosDialog(QDialog):
    """Escolher a quem pedir preços e preparar os emails.

    Os emails são **abertos no Outlook**, não enviados: o destinatário guardado
    é uma sugestão e quem envia é sempre uma pessoa.
    """

    TABLE_HEADERS = [
        "✓",
        "Fornecedor",
        "Materiais",
        "Preço mais antigo",
        "Email",
    ]

    HEADER_TOOLTIPS = [
        "Marque os fornecedores a quem quer pedir preços.",
        "Fornecedor dos materiais por rever.",
        "Quantos materiais entram no pedido.",
        "A data mais antiga do lote.",
        "Destinatário sugerido — pode ser alterado no Outlook antes de enviar.",
    ]

    COLUNA_VISTO = 0
    COLUNA_EMAIL = 4

    #: A partir daqui, abrir tantas janelas do Outlook de uma vez pede aviso.
    AVISO_MUITOS_EMAILS = 5

    def __init__(
        self,
        pedidos: list[PedidoFornecedor],
        parent=None,
        on_preparar: Callable[[list[PedidoFornecedor]], bool] | None = None,
        on_meses_mudou: Callable[[int], list[PedidoFornecedor]] | None = None,
        meses: int = MESES_PRECO_DESATUALIZADO,
    ) -> None:
        super().__init__(parent)

        self.pedidos = pedidos
        self.on_preparar = on_preparar
        self.on_meses_mudou = on_meses_mudou

        self.setWindowTitle("Pedir preços aos fornecedores")
        self.setModal(True)
        self.setMinimumSize(900, 520)
        self._dimensionar_ao_ecra()

        self.meses_input = QSpinBox()
        self.meses_input.setRange(1, 60)
        self.meses_input.setValue(meses)
        self.meses_input.setSuffix(" meses")
        self.meses_input.setToolTip(
            "Idade a partir da qual um preço entra no pedido de revisão."
        )
        self.meses_input.valueChanged.connect(self._recarregar)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        cabecalho = self.table.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        cabecalho.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        ligar_persistencia_larguras(self.table, "dialog_pedido_precos")
        for indice, tooltip in enumerate(self.HEADER_TOOLTIPS):
            item = self.table.horizontalHeaderItem(indice)
            if item is not None:
                item.setToolTip(tooltip)

        self.preparar_button = QPushButton("Preparar emails no Outlook")
        self.preparar_button.setToolTip(
            "Gera o anexo de cada fornecedor e abre a mensagem no Outlook. "
            "Nada é enviado: quem envia é sempre você."
        )
        self.preparar_button.clicked.connect(self._preparar)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.clicked.connect(self.reject)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        barra = QHBoxLayout()
        barra.addWidget(QLabel("Preços com mais de"))
        barra.addWidget(self.meses_input)
        barra.addStretch()

        botoes = QHBoxLayout()
        botoes.addStretch()
        botoes.addWidget(self.preparar_button)
        botoes.addWidget(self.fechar_button)

        layout = QVBoxLayout()
        layout.addLayout(barra)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        self._preencher()

    def _dimensionar_ao_ecra(self) -> None:
        """Abrir com espaço para a lista toda."""
        ecra = QGuiApplication.primaryScreen()
        if ecra is None:
            self.resize(1100, 700)
            return

        disponivel = ecra.availableGeometry()
        self.resize(
            max(min(int(disponivel.width() * 0.7), 1300), 900),
            max(min(int(disponivel.height() * 0.8), 900), 520),
        )

    def _preencher(self) -> None:
        """Encher a lista, com os que não têm email assinalados."""
        self.table.setRowCount(len(self.pedidos))

        for linha, pedido in enumerate(self.pedidos):
            visto = QTableWidgetItem()
            visto.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            # Só se pode pedir a quem tem email.
            visto.setCheckState(
                Qt.CheckState.Checked if pedido.tem_email else Qt.CheckState.Unchecked
            )
            self.table.setItem(linha, self.COLUNA_VISTO, visto)

            data = pedido.preco_mais_antigo
            valores = [
                pedido.fornecedor_nome,
                str(pedido.total),
                f"{data:%d-%m-%Y}" if data else "—",
                pedido.email or "— sem email —",
            ]
            for coluna, valor in enumerate(valores, start=1):
                item = QTableWidgetItem(valor)
                self.table.setItem(linha, coluna, item)

            if not pedido.tem_email:
                item = self.table.item(linha, self.COLUNA_EMAIL)
                item.setBackground(QColor(tema.VERMELHO_SUAVE))
                item.setToolTip(
                    "Preencha o email em «Fornecedores…» para poder pedir preços."
                )

        self.table.resizeColumnsToContents()
        self._atualizar_status()

    def _atualizar_status(self) -> None:
        """Linha do supervisor: o que se consegue pedir e o que falta."""
        total = sum(pedido.total for pedido in self.pedidos)
        sem_email = [pedido for pedido in self.pedidos if not pedido.tem_email]

        if not self.pedidos:
            self.status_label.setText(
                "Nenhum preço a rever com esta antiguidade — nada a pedir."
            )
            return

        texto = (
            f"{total} materiais a rever em {len(self.pedidos)} fornecedores."
        )
        if sem_email:
            nomes = ", ".join(pedido.fornecedor_nome for pedido in sem_email[:4])
            texto += (
                f" {len(sem_email)} sem email e por isso de fora: {nomes}"
                f"{'…' if len(sem_email) > 4 else ''}."
            )
        self.status_label.setText(texto)

    def pedidos_escolhidos(self) -> list[PedidoFornecedor]:
        """Os fornecedores marcados que têm mesmo para onde escrever."""
        escolhidos = []
        for linha, pedido in enumerate(self.pedidos):
            item = self.table.item(linha, self.COLUNA_VISTO)
            if (
                item is not None
                and item.checkState() == Qt.CheckState.Checked
                and pedido.tem_email
            ):
                escolhidos.append(pedido)

        return escolhidos

    def _recarregar(self, meses: int) -> None:
        """Refazer a lista quando muda a antiguidade pedida."""
        if self.on_meses_mudou is None:
            return

        self.pedidos = self.on_meses_mudou(meses)
        self._preencher()

    def _preparar(self) -> None:
        """Preparar os emails dos fornecedores escolhidos."""
        escolhidos = self.pedidos_escolhidos()
        if not escolhidos:
            self.status_label.setText(
                "Escolha pelo menos um fornecedor com email preenchido."
            )
            return

        if len(escolhidos) > self.AVISO_MUITOS_EMAILS:
            resposta = QMessageBox.question(
                self,
                "Preparar vários emails",
                f"Vão abrir-se {len(escolhidos)} mensagens no Outlook, uma por "
                "fornecedor. Continuar?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if resposta != QMessageBox.StandardButton.Yes:
                return

        if self.on_preparar is not None and not self.on_preparar(escolhidos):
            return

        self.accept()
