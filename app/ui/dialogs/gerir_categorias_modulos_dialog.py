"""Dialog to manage the module-library categories (phase 6).

Single-level categories (a customer name is fine). Create, rename, archive /
reactivate and safe-delete; a category in use by modules cannot be deleted
and OUTROS (the fallback) is protected.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.def_modulo_categoria_service import (
    DefModuloCategoriaService,
    ModuloCategoriaResumo,
)


class GerirCategoriasModulosDialog(QDialog):
    """Modal dialog to manage the module categories."""

    TABLE_HEADERS = ["Nome", "Código", "Módulos", "Estado"]

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.alterado = False
        self._categorias: list[ModuloCategoriaResumo] = []

        self.setWindowTitle("Gerir Categorias de Módulos")
        self.setModal(True)
        self.setMinimumSize(520, 420)

        self.nova_input = QLineEdit()
        self.nova_input.setPlaceholderText(
            "Nome da nova categoria (ex.: Roupeiros ou o nome de um cliente)"
        )
        self.nova_input.setToolTip("Nome da nova categoria de módulos")
        self.nova_input.returnPressed.connect(self._criar)
        self.criar_button = QPushButton("Criar")
        self.criar_button.setToolTip("Criar a categoria")
        self.criar_button.clicked.connect(self._criar)

        nova_layout = QHBoxLayout()
        nova_layout.addWidget(self.nova_input, stretch=1)
        nova_layout.addWidget(self.criar_button)

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.renomear_button = QPushButton("Renomear")
        self.renomear_button.setToolTip("Renomear a categoria selecionada")
        self.renomear_button.clicked.connect(self._renomear)
        self.arquivar_button = QPushButton("Arquivar")
        self.arquivar_button.setToolTip(
            "Arquivar/reativar: uma categoria arquivada sai das escolhas, "
            "mas os módulos antigos mantêm-na"
        )
        self.arquivar_button.clicked.connect(self._arquivar_ou_reativar)
        self.eliminar_button = QPushButton("Eliminar")
        self.eliminar_button.setToolTip(
            "Eliminar a categoria (apenas quando nenhum módulo a usa)"
        )
        self.eliminar_button.clicked.connect(self._eliminar)

        acoes_layout = QHBoxLayout()
        acoes_layout.addWidget(self.renomear_button)
        acoes_layout.addWidget(self.arquivar_button)
        acoes_layout.addWidget(self.eliminar_button)
        acoes_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.setToolTip("Fechar a gestão de categorias")
        self.fechar_button.clicked.connect(self.accept)

        fechar_layout = QHBoxLayout()
        fechar_layout.addStretch()
        fechar_layout.addWidget(self.fechar_button)

        layout = QVBoxLayout()
        layout.addLayout(nova_layout)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(acoes_layout)
        layout.addWidget(self.status_label)
        layout.addLayout(fechar_layout)
        self.setLayout(layout)

        self.table.itemSelectionChanged.connect(self._atualizar_botoes)
        self._carregar()

    # ----- data -----

    def _carregar(self) -> None:
        try:
            with SessionLocal() as session:
                self._categorias = DefModuloCategoriaService(session).listar()
                session.commit()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar as categorias.")
            return
        self._render()

    def _render(self) -> None:
        self.table.setRowCount(len(self._categorias))
        for row, categoria in enumerate(self._categorias):
            values = (
                categoria.nome,
                categoria.codigo,
                str(categoria.modulos_em_uso),
                "Ativa" if categoria.ativo else "Arquivada",
            )
            for col, texto in enumerate(values):
                item = QTableWidgetItem(texto)
                item.setToolTip(texto)
                self.table.setItem(row, col, item)
        self._atualizar_botoes()

    def _selecionada(self) -> ModuloCategoriaResumo | None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._categorias):
            return None
        return self._categorias[row]

    def _atualizar_botoes(self) -> None:
        categoria = self._selecionada()
        tem = categoria is not None
        self.renomear_button.setEnabled(tem)
        self.arquivar_button.setEnabled(tem)
        self.eliminar_button.setEnabled(tem)
        if categoria is not None:
            self.arquivar_button.setText(
                "Reativar" if not categoria.ativo else "Arquivar"
            )

    # ----- actions -----

    def _criar(self) -> None:
        nome = self.nova_input.text().strip()
        if not nome:
            self.status_label.setText("Escreva o nome da nova categoria.")
            return
        try:
            with SessionLocal() as session:
                DefModuloCategoriaService(session).criar(nome)
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível criar a categoria.")
            return
        self.alterado = True
        self.nova_input.clear()
        self.status_label.setText(f"Categoria {nome} criada.")
        self._carregar()

    def _renomear(self) -> None:
        categoria = self._selecionada()
        if categoria is None:
            return
        nome, ok = QInputDialog.getText(
            self,
            "Renomear categoria",
            "Novo nome:",
            text=categoria.nome,
        )
        if not ok or not nome.strip():
            return
        try:
            with SessionLocal() as session:
                DefModuloCategoriaService(session).renomear(
                    categoria.id, nome
                )
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível renomear a categoria.")
            return
        self.alterado = True
        self.status_label.setText(f"Categoria renomeada para {nome.strip()}.")
        self._carregar()

    def _arquivar_ou_reativar(self) -> None:
        categoria = self._selecionada()
        if categoria is None:
            return
        try:
            with SessionLocal() as session:
                service = DefModuloCategoriaService(session)
                if categoria.ativo:
                    service.arquivar(categoria.id)
                    mensagem = f"Categoria {categoria.nome} arquivada."
                else:
                    service.reativar(categoria.id)
                    mensagem = f"Categoria {categoria.nome} reativada."
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível alterar a categoria.")
            return
        self.alterado = True
        self.status_label.setText(mensagem)
        self._carregar()

    def _eliminar(self) -> None:
        categoria = self._selecionada()
        if categoria is None:
            return
        resposta = QMessageBox.question(
            self,
            "Eliminar categoria",
            f"Eliminar a categoria {categoria.nome}?\n\n"
            "Só é possível quando nenhum módulo a usa.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if resposta != QMessageBox.StandardButton.Yes:
            return
        try:
            with SessionLocal() as session:
                DefModuloCategoriaService(session).eliminar(categoria.id)
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível eliminar a categoria.")
            return
        self.alterado = True
        self.status_label.setText(f"Categoria {categoria.nome} eliminada.")
        self._carregar()
