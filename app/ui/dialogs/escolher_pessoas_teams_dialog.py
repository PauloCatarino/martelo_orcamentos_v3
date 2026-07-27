"""Escolher a quem vai o ticket no Teams."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from app.ui import tema


class EscolherPessoasTeamsDialog(QDialog):
    """Pick one or more people to send the ticket to.

    Com mais do que uma pessoa o Teams abre uma conversa de grupo com todas —
    é o que serve quando o mesmo problema é de duas.
    """

    def __init__(self, parent=None, *, membros=(), pre_selecionados=()) -> None:
        super().__init__(parent)

        self._membros = list(membros or ())
        pre = {int(identificador) for identificador in pre_selecionados or ()}

        self.setWindowTitle("Enviar para Teams")
        self.setModal(True)
        self.resize(460, 460)

        cabecalho = QLabel(
            "A quem vai este ticket? Escolhendo mais do que uma pessoa, o Teams "
            "abre uma conversa de grupo com todas."
        )
        cabecalho.setWordWrap(True)
        cabecalho.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        self.lista = QListWidget()
        self.lista.setToolTip("Marque quem tem de ficar a par deste ticket")
        self.lista.itemChanged.connect(lambda _item: self._atualizar_estado())

        for membro in self._membros:
            tem_endereco = bool((membro.email or "").strip())
            item = QListWidgetItem(self._rotulo(membro, tem_endereco))
            item.setData(Qt.ItemDataRole.UserRole, int(membro.id))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if (tem_endereco and int(membro.id) in pre)
                else Qt.CheckState.Unchecked
            )
            if not tem_endereco:
                # Sem endereço não há conversa para abrir; fica visível para o
                # utilizador perceber que falta preencher a Equipa.
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                item.setToolTip("Falta o endereço de Teams desta pessoa (Equipa…)")
            self.lista.addItem(item)

        self.enviar_button = QPushButton("Abrir no Teams")
        self.enviar_button.setToolTip("Abrir a conversa com o ticket já escrito")
        self.enviar_button.setDefault(True)
        self.enviar_button.clicked.connect(self.accept)

        self.copiar_button = QPushButton("Só copiar o ticket")
        self.copiar_button.setToolTip(
            "Copiar o ticket e as fotos sem abrir o Teams, para colar onde quiser"
        )
        self.copiar_button.clicked.connect(self._so_copiar)

        self.cancelar_button = QPushButton("Cancelar")
        self.cancelar_button.clicked.connect(self.reject)

        botoes = QHBoxLayout()
        botoes.addWidget(self.copiar_button)
        botoes.addStretch()
        botoes.addWidget(self.enviar_button)
        botoes.addWidget(self.cancelar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("escolherPessoasStatus")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(cabecalho)
        layout.addWidget(self.lista, stretch=1)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self._so_copiar_pedido = False
        self._atualizar_estado()

    # ---- leitura ---------------------------------------------------------
    def escolhidos(self) -> list:
        """Team members the user ticked."""
        marcados = set()
        for indice in range(self.lista.count()):
            item = self.lista.item(indice)
            if item.checkState() == Qt.CheckState.Checked:
                marcados.add(int(item.data(Qt.ItemDataRole.UserRole)))
        return [membro for membro in self._membros if int(membro.id) in marcados]

    def apenas_copiar(self) -> bool:
        """True when the user chose to copy without opening Teams."""
        return self._so_copiar_pedido

    # ---- apoio -----------------------------------------------------------
    @staticmethod
    def _rotulo(membro, tem_endereco: bool) -> str:
        if tem_endereco:
            return f"{membro.nome}  —  {membro.email}"
        return f"{membro.nome}  —  (sem endereço de Teams)"

    def _atualizar_estado(self) -> None:
        total = len(self.escolhidos())
        self.enviar_button.setEnabled(total > 0)
        if total == 0:
            self.status_label.setText("Escolha pelo menos uma pessoa.")
        elif total == 1:
            self.status_label.setText("Abre a conversa desta pessoa.")
        else:
            self.status_label.setText(
                f"Abre uma conversa de grupo com {total} pessoas."
            )

    def _so_copiar(self) -> None:
        self._so_copiar_pedido = True
        self.accept()
