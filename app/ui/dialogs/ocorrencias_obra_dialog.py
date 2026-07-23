"""Dialog with the diary of one production work (obra)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.services.producao_ocorrencias_service import (
    eliminar_ocorrencia,
    formatar_data,
    listar_ocorrencias,
    registar_ocorrencia,
)
from app.ui import tema


class OcorrenciasObraDialog(QDialog):
    """Read and add lines to one obra's diary.

    Serve para o que os clientes reportam depois da entrega e para notas que
    não devem sujar os campos da obra.
    """

    def __init__(self, *, producao_id: int, codigo_processo: str, parent=None) -> None:
        super().__init__(parent)

        self._producao_id = producao_id

        self.setWindowTitle(f"Registo de ocorrências — {codigo_processo}")
        self.setModal(True)
        self.resize(900, 620)

        cabecalho = QLabel(
            "Diário desta obra: o que o cliente reportou, o que se combinou, o "
            "que correu mal. Cada registo fica com a data e o nome de quem "
            "escreveu, e não altera nada nos dados da obra."
        )
        cabecalho.setWordWrap(True)
        cabecalho.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Quando", "Quem", "O que aconteceu"])
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setWordWrap(True)
        cabecalho_tabela = self.table.horizontalHeader()
        cabecalho_tabela.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        cabecalho_tabela.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 130)
        self.table.setColumnWidth(1, 140)

        self.texto_input = QTextEdit()
        self.texto_input.setAcceptRichText(False)
        self.texto_input.setMinimumHeight(90)
        self.texto_input.setPlaceholderText(
            "Escreva o que aconteceu. Ex.: cliente diz que faltou uma dobradiça "
            "no roupeiro do quarto 2; combinado levar na próxima entrega."
        )
        self.texto_input.setToolTip("O que aconteceu nesta obra")

        self.registar_button = QPushButton("Registar")
        self.registar_button.setToolTip("Acrescentar este registo ao diário da obra")
        self.registar_button.clicked.connect(self._registar)

        self.eliminar_button = QPushButton("Eliminar registo")
        self.eliminar_button.setToolTip(
            "Eliminar o registo selecionado — só quem o escreveu"
        )
        self.eliminar_button.clicked.connect(self._eliminar)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.clicked.connect(self.accept)

        botoes = QHBoxLayout()
        botoes.addWidget(self.registar_button)
        botoes.addWidget(self.eliminar_button)
        botoes.addStretch()
        botoes.addWidget(self.fechar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("ocorrenciasStatus")

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.addWidget(cabecalho)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(QLabel("Novo registo"))
        layout.addWidget(self.texto_input)
        layout.addLayout(botoes)
        layout.addWidget(self.status_label)

        self.carregar()

    # ---- dados -----------------------------------------------------------
    def carregar(self) -> None:
        """Load this obra's diary."""
        self.table.setRowCount(0)
        try:
            with SessionLocal() as session:
                linhas = [
                    (o.id, formatar_data(o.created_at), o.autor or "—", o.texto)
                    for o in listar_ocorrencias(session, self._producao_id)
                ]
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar os registos.")
            return

        self.table.setRowCount(len(linhas))
        for indice, (ocorrencia_id, quando, quem, texto) in enumerate(linhas):
            item_quando = QTableWidgetItem(quando)
            item_quando.setData(Qt.ItemDataRole.UserRole, ocorrencia_id)
            self.table.setItem(indice, 0, item_quando)
            self.table.setItem(indice, 1, QTableWidgetItem(quem))
            item_texto = QTableWidgetItem(texto)
            item_texto.setToolTip(texto)
            self.table.setItem(indice, 2, item_texto)
        self.table.resizeRowsToContents()

        if not linhas:
            self.status_label.setText("Sem registos nesta obra.")
        else:
            self.status_label.setText(
                f"{len(linhas)} registo(s), do mais recente para o mais antigo."
            )

    def _registar(self) -> None:
        utilizador = app_session.current_user
        try:
            with SessionLocal() as session:
                registar_ocorrencia(
                    session,
                    producao_id=self._producao_id,
                    texto=self.texto_input.toPlainText(),
                    user_id=getattr(utilizador, "id", None),
                    autor=getattr(utilizador, "nome", None)
                    or getattr(utilizador, "username", None),
                )
                session.commit()
        except ValueError as erro:
            self.status_label.setText(str(erro))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível gravar o registo.")
            return

        self.texto_input.clear()
        self.carregar()
        self.status_label.setText("Registo acrescentado.")

    def _eliminar(self) -> None:
        linha = self.table.currentRow()
        if linha < 0:
            self.status_label.setText("Selecione um registo para eliminar.")
            return

        item = self.table.item(linha, 0)
        if item is None:
            return
        ocorrencia_id = int(item.data(Qt.ItemDataRole.UserRole))

        resposta = QMessageBox.question(
            self,
            "Eliminar registo",
            "Eliminar este registo do diário da obra?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return

        utilizador = app_session.current_user
        try:
            with SessionLocal() as session:
                eliminar_ocorrencia(
                    session,
                    ocorrencia_id,
                    user_id=getattr(utilizador, "id", None),
                    is_admin=str(getattr(utilizador, "role", "")).lower() == "admin",
                )
                session.commit()
        except ValueError as erro:
            self.status_label.setText(str(erro))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível eliminar o registo.")
            return

        self.carregar()
        self.status_label.setText("Registo eliminado.")
