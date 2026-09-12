"""Escolher chaves e modelos de destino, com a conta exata do que vai mudar."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QRadioButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.services.def_valueset_chave_copia_service import (
    ACRESCENTAR_E_ATUALIZAR,
    SO_ACRESCENTAR,
    ChaveDisponivel,
    ContextoCopiaChaves,
)
from app.ui.tema import CINZA_ESCURO, TEXTO_AVISO, VERDE_ESCURO


class CopiarChavesValuesetDialog(QDialog):
    """Copiar chaves de um modelo ValueSet para outros, com pré-visualização.

    Nada é escrito enquanto esta janela estiver aberta: a conta de cada destino
    refaz-se a cada mudança de chave ou de modo, e só o botão Copiar grava.
    """

    CHAVES_HEADERS = ["", "Grupo", "Chave", "Código", "Opções"]
    DESTINOS_HEADERS = [
        "",
        "Modelo",
        "Nome",
        "Tipo",
        "Âmbito",
        "Dono",
        "A criar",
        "A atualizar",
        "Já iguais",
        "Só no destino",
    ]

    def __init__(
        self,
        modelo_codigo: str,
        chaves: tuple[ChaveDisponivel, ...],
        recalcular: Callable[[list[str], str], ContextoCopiaChaves],
        *,
        chaves_iniciais: list[str] | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._recalcular = recalcular
        self._chaves = chaves
        self._contexto: ContextoCopiaChaves | None = None
        self._a_preencher = False

        self.setWindowTitle("Copiar chaves para outros modelos")
        self.setModal(True)
        self.setMinimumSize(1100, 650)

        info = QLabel(
            f"Origem: <b>{modelo_codigo}</b>. Escolha as chaves e os modelos de "
            "destino. <b>Nada é apagado no destino</b> — uma opção que só exista "
            "lá fica onde está."
        )
        info.setWordWrap(True)

        self.chaves_table = self._criar_tabela(self.CHAVES_HEADERS)
        self.chaves_table.itemChanged.connect(self._on_chave_mudou)
        self._preencher_chaves(chaves_iniciais or [])

        self.modo_acrescentar = QRadioButton("Só acrescentar o que falta")
        self.modo_acrescentar.setToolTip(
            "Cria as opções que o destino não tem. As que já lá estão não são "
            "tocadas, mesmo que estejam diferentes."
        )
        self.modo_acrescentar.setChecked(True)
        self.modo_atualizar = QRadioButton(
            "Acrescentar e atualizar as que já existem"
        )
        self.modo_atualizar.setToolTip(
            "Além de criar o que falta, põe as opções comuns iguais às da "
            "origem: material, preços, prioridade e operações."
        )
        self._grupo_modo = QButtonGroup(self)
        self._grupo_modo.addButton(self.modo_acrescentar)
        self._grupo_modo.addButton(self.modo_atualizar)
        self._grupo_modo.buttonToggled.connect(
            lambda _b, marcado: self._atualizar_previsao() if marcado else None
        )

        modo_layout = QHBoxLayout()
        modo_layout.setSpacing(12)
        modo_layout.addWidget(QLabel("Se o destino já tiver a opção:"))
        modo_layout.addWidget(self.modo_acrescentar)
        modo_layout.addWidget(self.modo_atualizar)
        modo_layout.addStretch()

        self.destinos_table = self._criar_tabela(self.DESTINOS_HEADERS)
        self.destinos_table.itemChanged.connect(self._on_destino_mudou)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.botao_copiar = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.botao_copiar.setText("Copiar")
        self.botao_copiar.setToolTip(
            "Criar e atualizar as linhas contadas acima, nos modelos marcados."
        )
        cancelar = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancelar.setToolTip("Sair sem copiar nada.")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._envolver("Chaves a copiar", self.chaves_table))
        splitter.addWidget(self._envolver("Modelos de destino", self.destinos_table))
        splitter.setSizes([250, 350])

        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.addWidget(info)
        layout.addLayout(modo_layout)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(self.status_label)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

        self._atualizar_previsao()

    # ----- o que a página lê no fim -----

    @property
    def modo(self) -> str:
        """O modo escolhido."""
        return (
            ACRESCENTAR_E_ATUALIZAR
            if self.modo_atualizar.isChecked()
            else SO_ACRESCENTAR
        )

    @property
    def chaves_escolhidas(self) -> list[str]:
        """As chaves marcadas, pela ordem em que aparecem."""
        escolhidas = []
        for row in range(self.chaves_table.rowCount()):
            item = self.chaves_table.item(row, 0)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                escolhidas.append(self._chaves[row].chave)
        return escolhidas

    @property
    def destinos_escolhidos(self) -> list[int]:
        """Os ids dos modelos marcados."""
        if self._contexto is None:
            return []
        escolhidos = []
        for row, destino in enumerate(self._contexto.destinos):
            item = self.destinos_table.item(row, 0)
            if item is not None and item.checkState() == Qt.CheckState.Checked:
                escolhidos.append(destino.modelo_id)
        return escolhidos

    @property
    def contexto(self) -> ContextoCopiaChaves | None:
        """A pré-visualização que está à frente do utilizador."""
        return self._contexto

    # ----- interior -----

    def _criar_tabela(self, headers: list[str]) -> QTableWidget:
        tabela = QTableWidget(0, len(headers))
        tabela.setHorizontalHeaderLabels(headers)
        tabela.verticalHeader().setVisible(False)
        tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        cabecalho = tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        cabecalho.setStretchLastSection(True)
        return tabela

    @staticmethod
    def _envolver(titulo: str, tabela: QTableWidget) -> QWidget:
        rotulo = QLabel(titulo)
        fonte = rotulo.font()
        fonte.setBold(True)
        rotulo.setFont(fonte)
        caixa = QWidget()
        disposicao = QVBoxLayout()
        disposicao.setContentsMargins(0, 0, 0, 0)
        disposicao.setSpacing(4)
        disposicao.addWidget(rotulo)
        disposicao.addWidget(tabela, stretch=1)
        caixa.setLayout(disposicao)
        return caixa

    def _preencher_chaves(self, iniciais: list[str]) -> None:
        marcadas = {(c or "").strip().upper() for c in iniciais}
        self._a_preencher = True
        self.chaves_table.setRowCount(len(self._chaves))
        for row, chave in enumerate(self._chaves):
            marca = QTableWidgetItem()
            marca.setFlags(
                Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
            )
            marca.setCheckState(
                Qt.CheckState.Checked
                if chave.chave in marcadas
                else Qt.CheckState.Unchecked
            )
            self.chaves_table.setItem(row, 0, marca)
            for coluna, texto in enumerate(
                (chave.grupo, chave.nome, chave.chave, str(chave.opcoes)), start=1
            ):
                self.chaves_table.setItem(row, coluna, QTableWidgetItem(texto))
        self._a_preencher = False

    def _on_chave_mudou(self, item: QTableWidgetItem) -> None:
        if self._a_preencher or item.column() != 0:
            return
        self._atualizar_previsao()

    def _on_destino_mudou(self, item: QTableWidgetItem) -> None:
        if self._a_preencher or item.column() != 0:
            return
        self._atualizar_estado()

    def _atualizar_previsao(self) -> None:
        """Refazer a conta de cada destino com as escolhas atuais."""
        chaves = self.chaves_escolhidas
        if not chaves:
            self._contexto = None
            self._a_preencher = True
            self.destinos_table.setRowCount(0)
            self._a_preencher = False
            self._atualizar_estado()
            return

        try:
            self._contexto = self._recalcular(chaves, self.modo)
        except (ValueError, PermissionError) as error:
            self._contexto = None
            self._a_preencher = True
            self.destinos_table.setRowCount(0)
            self._a_preencher = False
            self.status_label.setStyleSheet(f"color: {TEXTO_AVISO};")
            self.status_label.setText(str(error))
            self.botao_copiar.setEnabled(False)
            return

        self._preencher_destinos()
        self._atualizar_estado()

    def _preencher_destinos(self) -> None:
        destinos = self._contexto.destinos if self._contexto else tuple()
        self._a_preencher = True
        self.destinos_table.setRowCount(len(destinos))
        for row, destino in enumerate(destinos):
            marca = QTableWidgetItem()
            if destino.permitido and not destino.sem_efeito:
                marca.setFlags(
                    Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled
                )
                marca.setCheckState(Qt.CheckState.Unchecked)
            else:
                # Sem permissão ou sem nada para fazer: não se marca.
                marca.setFlags(Qt.ItemFlag.NoItemFlags)
                marca.setCheckState(Qt.CheckState.Unchecked)
                marca.setToolTip(
                    destino.motivo_bloqueio
                    or "Neste modelo não há nada a criar nem a atualizar."
                )
            self.destinos_table.setItem(row, 0, marca)

            valores = (
                destino.modelo_codigo,
                destino.modelo_nome,
                destino.tipo,
                destino.ambito,
                destino.proprietario,
                str(destino.total_a_criar),
                str(destino.total_a_atualizar),
                str(sum(p.iguais for p in destino.previsoes)),
                str(sum(p.so_no_destino for p in destino.previsoes)),
            )
            for coluna, texto in enumerate(valores, start=1):
                item = QTableWidgetItem(texto)
                if coluna >= 6:
                    item.setTextAlignment(
                        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
                    )
                if not destino.permitido:
                    item.setToolTip(destino.motivo_bloqueio or "")
                self.destinos_table.setItem(row, coluna, item)
        self._a_preencher = False

    def _atualizar_estado(self) -> None:
        """Dizer o que vai acontecer, e ligar o botão só quando há o quê."""
        chaves = self.chaves_escolhidas
        destinos = self.destinos_escolhidos
        if not chaves:
            self.status_label.setStyleSheet(f"color: {CINZA_ESCURO};")
            self.status_label.setText("Escolha pelo menos uma chave para copiar.")
            self.botao_copiar.setEnabled(False)
            return
        if not destinos:
            self.status_label.setStyleSheet(f"color: {CINZA_ESCURO};")
            self.status_label.setText(
                f"{len(chaves)} chave(s) escolhidas. Marque os modelos de destino."
            )
            self.botao_copiar.setEnabled(False)
            return

        contexto = self._contexto
        por_id = {d.modelo_id: d for d in (contexto.destinos if contexto else tuple())}
        criar = sum(por_id[i].total_a_criar for i in destinos if i in por_id)
        atualizar = sum(por_id[i].total_a_atualizar for i in destinos if i in por_id)
        self.status_label.setStyleSheet(f"color: {VERDE_ESCURO};")
        self.status_label.setText(
            f"{len(chaves)} chave(s) para {len(destinos)} modelo(s): "
            f"{criar} linha(s) a criar e {atualizar} a atualizar. "
            "Nada é apagado."
        )
        self.botao_copiar.setEnabled(criar + atualizar > 0)
