"""Dialog to manage and pick user predefined descriptions (phase P6a)."""

from __future__ import annotations
from app.ui import tema

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QDialog, QDialogButtonBox, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.descricao_predefinida_service import DescricaoPredefinidaService

_VERDE = tema.TEXTO_OK


@dataclass(frozen=True)
class DescricaoEscolhida:
    id: int
    texto: str
    tipo: str


class _EditorDescricaoDialog(QDialog):
    def __init__(self, parent=None, *, titulo: str, texto: str = "", tipo: str = "-") -> None:
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.setMinimumWidth(420)
        self.edit_texto = QLineEdit(texto)
        self.edit_texto.setPlaceholderText("Descrição")
        self.combo_tipo = QComboBox()
        self.combo_tipo.addItem("- Marcador", "-")
        self.combo_tipo.addItem("* Destaque verde", "*")
        if (tipo or "").strip() == "*":
            self.combo_tipo.setCurrentIndex(1)
        botoes = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        botoes.accepted.connect(self._accept)
        botoes.rejected.connect(self.reject)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Texto da descrição:"))
        layout.addWidget(self.edit_texto)
        layout.addWidget(QLabel("Tipo:"))
        layout.addWidget(self.combo_tipo)
        layout.addWidget(botoes)
        self.setLayout(layout)

    def texto_value(self) -> str:
        return self.edit_texto.text().strip()

    def tipo_value(self) -> str:
        return self.combo_tipo.currentData() or "-"

    def _accept(self) -> None:
        if not self.texto_value():
            QMessageBox.warning(self, "Descrições", "Indique o texto da descrição.")
            return
        self.accept()


class DescricoesPredefinidasDialog(QDialog):
    def __init__(self, parent=None, *, user_id: int | None = None) -> None:
        super().__init__(parent)
        self._user_id = user_id
        self.setWindowTitle("Descrições pré-definidas")
        self.setMinimumSize(520, 520)

        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText("Pesquisar (use % para separar palavras)")
        self.edit_search.setClearButtonEnabled(True)
        self.edit_search.textChanged.connect(self._aplicar_filtro)

        self.lista = QListWidget()
        self.lista.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

        self.btn_add = QPushButton("Adicionar")
        self.btn_edit = QPushButton("Editar")
        self.btn_remove = QPushButton("Eliminar")
        self.btn_up = QPushButton("▲")
        self.btn_down = QPushButton("▼")
        self.btn_add.clicked.connect(self._on_add)
        self.btn_edit.clicked.connect(self._on_edit)
        self.btn_remove.clicked.connect(self._on_remove)
        self.btn_up.clicked.connect(lambda: self._mover("up"))
        self.btn_down.clicked.connect(lambda: self._mover("down"))
        btn_row = QHBoxLayout()
        for b in (self.btn_add, self.btn_edit, self.btn_remove, self.btn_up, self.btn_down):
            btn_row.addWidget(b)

        self.btn_insert = QPushButton("Inserir")
        self.btn_insert.setDefault(True)
        self.btn_cancel = QPushButton("Cancelar")
        self.btn_insert.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        acao_row = QHBoxLayout()
        acao_row.addWidget(self.btn_insert)
        acao_row.addWidget(self.btn_cancel)

        layout = QVBoxLayout()
        layout.addWidget(self.edit_search)
        layout.addWidget(self.lista, stretch=1)
        layout.addLayout(btn_row)
        layout.addLayout(acao_row)
        self.setLayout(layout)

        self._carregar()

    def _carregar(self) -> None:
        self.lista.clear()
        if not self._user_id:
            return
        try:
            with SessionLocal() as session:
                rows = DescricaoPredefinidaService(session).listar(self._user_id)
        except SQLAlchemyError:
            QMessageBox.warning(self, "Descrições", "Não foi possível carregar as descrições.")
            return
        for row in rows:
            item = QListWidgetItem(f"{row.tipo} {row.texto}")
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(
                Qt.ItemDataRole.UserRole, DescricaoEscolhida(row.id, row.texto, row.tipo)
            )
            if row.tipo == "*":
                fonte = item.font()
                fonte.setItalic(True)
                item.setFont(fonte)
                item.setForeground(QBrush(QColor(_VERDE)))
            self.lista.addItem(item)
        self._aplicar_filtro(self.edit_search.text())

    def _aplicar_filtro(self, texto: str) -> None:
        termos = [t.strip().lower() for t in (texto or "").split("%") if t.strip()]
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            linha = (item.text() or "").lower()
            item.setHidden(bool(termos) and not all(t in linha for t in termos))

    def _registo_atual(self) -> DescricaoEscolhida | None:
        item = self.lista.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def _on_add(self) -> None:
        if not self._user_id:
            return
        dlg = _EditorDescricaoDialog(self, titulo="Adicionar descrição")
        if not dlg.exec():
            return
        self._executar(
            lambda s: DescricaoPredefinidaService(s).criar(
                self._user_id, dlg.texto_value(), dlg.tipo_value()
            )
        )

    def _on_edit(self) -> None:
        registo = self._registo_atual()
        if registo is None:
            return
        dlg = _EditorDescricaoDialog(
            self, titulo="Editar descrição", texto=registo.texto, tipo=registo.tipo
        )
        if not dlg.exec():
            return
        self._executar(
            lambda s: DescricaoPredefinidaService(s).editar(
                registo.id, self._user_id, dlg.texto_value(), dlg.tipo_value()
            )
        )

    def _on_remove(self) -> None:
        ids = [
            self.lista.item(i).data(Qt.ItemDataRole.UserRole).id
            for i in range(self.lista.count())
            if self.lista.item(i).isSelected()
        ]
        if not ids:
            return
        if QMessageBox.question(
            self, "Descrições", "Eliminar as descrições selecionadas?"
        ) != QMessageBox.StandardButton.Yes:
            return
        self._executar(lambda s: DescricaoPredefinidaService(s).eliminar(self._user_id, ids))

    def _mover(self, direcao: str) -> None:
        registo = self._registo_atual()
        if registo is None:
            return
        self._executar(
            lambda s: DescricaoPredefinidaService(s).mover(registo.id, self._user_id, direcao)
        )

    def _executar(self, accao) -> None:
        try:
            with SessionLocal() as session:
                accao(session)
        except (SQLAlchemyError, ValueError) as exc:
            QMessageBox.warning(self, "Descrições", str(exc))
            return
        self._carregar()

    def checked_entries(self) -> list[DescricaoEscolhida]:
        entries: list[DescricaoEscolhida] = []
        for i in range(self.lista.count()):
            item = self.lista.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                dados = item.data(Qt.ItemDataRole.UserRole)
                if dados is not None:
                    entries.append(dados)
        return entries
