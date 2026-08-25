"""Dialog for managing suppliers and, above all, their email addresses."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.repositories.def_fornecedor_repository import DefFornecedorResumo
from app.services.def_fornecedor_service import FornecedorData
from app.ui import tema
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class FornecedoresDialog(QDialog):
    """Lista de fornecedores com as células editáveis.

    Foi feito para uma tarefa concreta: preencher de uma assentada os emails que
    faltam, para o pedido de preços poder existir. Por isso a tabela edita-se
    diretamente, em vez de obrigar a abrir uma ficha por fornecedor.
    """

    TABLE_HEADERS = [
        "Fornecedor",
        "Email",
        "Email CC",
        "Pessoa de contacto",
        "Telefone",
        "Materiais",
    ]

    HEADER_TOOLTIPS = [
        "Nome do fornecedor.",
        "Destinatário sugerido do pedido de preços — pode ser alterado no envio.",
        "Endereço em cópia, quando faz sentido.",
        "Quem costuma responder.",
        "Telefone de contacto.",
        "Matérias-primas ativas fornecidas por este fornecedor.",
    ]

    COLUNA_NOME = 0
    COLUNA_EMAIL = 1
    COLUNA_CC = 2
    COLUNA_CONTACTO = 3
    COLUNA_TELEFONE = 4
    COLUNA_MATERIAIS = 5

    def __init__(
        self,
        fornecedores: list[DefFornecedorResumo],
        parent=None,
        on_save: Callable[[dict[int, FornecedorData]], bool] | None = None,
        on_criar: Callable[[str], list[DefFornecedorResumo] | None] | None = None,
        on_ligar_pelo_nome: Callable[[], tuple[str, list[DefFornecedorResumo]] | None]
        | None = None,
    ) -> None:
        super().__init__(parent)

        self.fornecedores = fornecedores
        self.on_save = on_save
        self.on_criar = on_criar
        self.on_ligar_pelo_nome = on_ligar_pelo_nome

        self.setWindowTitle("Fornecedores")
        self.setModal(True)
        self.setMinimumSize(1000, 620)
        self._dimensionar_ao_ecra()

        self.info_label = QLabel(
            "Os emails aqui guardados são a sugestão de destinatário do pedido de "
            "preços. No envio pode alterá-los e acrescentar cópia."
        )
        self.info_label.setWordWrap(True)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        cabecalho = self.table.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        cabecalho.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
        ligar_persistencia_larguras(self.table, "dialog_fornecedores")
        for indice, tooltip in enumerate(self.HEADER_TOOLTIPS):
            item = self.table.horizontalHeaderItem(indice)
            if item is not None:
                item.setToolTip(tooltip)

        self.nome_novo_input = QLineEdit()
        self.nome_novo_input.setPlaceholderText("Nome do fornecedor novo…")
        self.nome_novo_input.setToolTip("Escreva o nome e clique em «Acrescentar».")

        self.criar_button = QPushButton("Acrescentar")
        self.criar_button.setToolTip("Criar um fornecedor novo")
        self.criar_button.clicked.connect(self._criar_fornecedor)

        self.ligar_button = QPushButton("Ligar materiais pelo nome")
        self.ligar_button.setToolTip(
            "Percorre o catálogo e liga a este fornecedor as matérias-primas que "
            "têm o mesmo nome escrito. Útil depois de uma importação."
        )
        self.ligar_button.setVisible(on_ligar_pelo_nome is not None)
        self.ligar_button.clicked.connect(self._ligar_pelo_nome)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Save).setText("Guardar")
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).setText("Fechar")
        self.button_box.accepted.connect(self._guardar)
        self.button_box.rejected.connect(self.reject)

        barra = QHBoxLayout()
        barra.addWidget(self.nome_novo_input)
        barra.addWidget(self.criar_button)
        barra.addStretch()
        barra.addWidget(self.ligar_button)

        layout = QVBoxLayout()
        layout.addWidget(self.info_label)
        layout.addLayout(barra)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.button_box)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

        self._preencher()

    def _dimensionar_ao_ecra(self) -> None:
        """Abrir grande: são muitos fornecedores e a coluna do email é larga."""
        ecra = QGuiApplication.primaryScreen()
        if ecra is None:
            self.resize(1300, 800)
            return

        disponivel = ecra.availableGeometry()
        largura = min(int(disponivel.width() * 0.85), 1500)
        altura = min(int(disponivel.height() * 0.88), 950)
        self.resize(max(largura, 1000), max(altura, 620))

    def _preencher(self) -> None:
        """Encher a tabela e assinalar quem fornece material mas não tem email."""
        self.table.setRowCount(len(self.fornecedores))

        for linha, fornecedor in enumerate(self.fornecedores):
            valores = [
                fornecedor.nome,
                fornecedor.email or "",
                fornecedor.email_cc or "",
                fornecedor.pessoa_contacto or "",
                fornecedor.telefone or "",
                str(fornecedor.materias_primas),
            ]
            for coluna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                if coluna == self.COLUNA_MATERIAIS:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(linha, coluna, item)

            if fornecedor.materias_primas and not fornecedor.tem_email:
                # Fornece material mas não há para onde escrever.
                item = self.table.item(linha, self.COLUNA_EMAIL)
                item.setBackground(QColor(tema.VERMELHO_SUAVE))
                item.setToolTip(
                    "Sem email não é possível pedir preços a este fornecedor."
                )

        self.table.resizeColumnsToContents()
        self._atualizar_status()

    def _atualizar_status(self) -> None:
        """Linha do supervisor: quantos ainda não têm para onde escrever."""
        sem_email = [
            fornecedor
            for fornecedor in self.fornecedores
            if fornecedor.materias_primas and not fornecedor.tem_email
        ]
        if sem_email:
            nomes = ", ".join(fornecedor.nome for fornecedor in sem_email[:5])
            resto = "…" if len(sem_email) > 5 else ""
            self.status_label.setText(
                f"{len(sem_email)} fornecedores com material mas sem email: {nomes}{resto}"
            )
        else:
            self.status_label.setText(
                f"{len(self.fornecedores)} fornecedores · todos com email."
            )

    def alteracoes(self) -> dict[int, FornecedorData]:
        """O que mudou na tabela, por id de fornecedor."""
        mudancas: dict[int, FornecedorData] = {}

        for linha, fornecedor in enumerate(self.fornecedores):
            dados = FornecedorData(
                nome=self._celula(linha, self.COLUNA_NOME) or fornecedor.nome,
                email=self._celula(linha, self.COLUNA_EMAIL),
                email_cc=self._celula(linha, self.COLUNA_CC),
                pessoa_contacto=self._celula(linha, self.COLUNA_CONTACTO),
                telefone=self._celula(linha, self.COLUNA_TELEFONE),
                observacoes=fornecedor.observacoes,
                ativo=fornecedor.ativo,
            )
            atual = FornecedorData(
                nome=fornecedor.nome,
                email=fornecedor.email,
                email_cc=fornecedor.email_cc,
                pessoa_contacto=fornecedor.pessoa_contacto,
                telefone=fornecedor.telefone,
                observacoes=fornecedor.observacoes,
                ativo=fornecedor.ativo,
            )
            if dados != atual:
                mudancas[fornecedor.id] = dados

        return mudancas

    def _celula(self, linha: int, coluna: int) -> str | None:
        item = self.table.item(linha, coluna)
        texto = (item.text() if item is not None else "").strip()
        return texto or None

    def _criar_fornecedor(self) -> None:
        """Criar um fornecedor a partir do nome escrito na barra.

        O criador devolve a lista já atualizada (ou None se não conseguiu), para
        o fornecedor novo aparecer sem ser preciso fechar e voltar a abrir.
        """
        nome = self.nome_novo_input.text().strip()
        if not nome:
            self.status_label.setText("Escreva o nome do fornecedor a acrescentar.")
            return

        if self.on_criar is None:
            return

        atualizados = self.on_criar(nome)
        if atualizados is None:
            return

        self.nome_novo_input.clear()
        self.fornecedores = atualizados
        self._preencher()
        self.status_label.setText(f"Fornecedor «{nome}» criado.")

    def _ligar_pelo_nome(self) -> None:
        """Repor as ligações entre matérias-primas e fornecedores, pelo nome."""
        if self.on_ligar_pelo_nome is None:
            return

        resultado = self.on_ligar_pelo_nome()
        if resultado is None:
            return

        mensagem, atualizados = resultado
        self.fornecedores = atualizados
        self._preencher()
        self.status_label.setText(mensagem)

    def _guardar(self) -> None:
        """Gravar as alterações da tabela."""
        mudancas = self.alteracoes()
        if not mudancas:
            self.accept()
            return

        if self.on_save is not None and not self.on_save(mudancas):
            return

        self.accept()
