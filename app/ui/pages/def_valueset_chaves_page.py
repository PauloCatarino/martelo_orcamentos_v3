"""Page for managing configurable ValueSet keys."""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.def_valueset_chave_repository import DefValuesetChaveResumo
from app.services.def_valueset_chave_service import (
    CriarDefValuesetChaveData,
    DefValuesetChaveService,
    EditarDefValuesetChaveData,
)
from app.ui.dialogs.def_valueset_chave_dialog import DefValuesetChaveDialog
from app.ui.helpers.erros import mensagem_erro_bd
from app.ui.tema import (
    CINZA_ESCURO,
    ESTILO_TABELA_CONFIG,
    cor_grupo_chave,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class DefValuesetChavesPage(QWidget):
    """Admin page for managing configurable ValueSet keys."""

    TABLE_HEADERS = [
        "Código",
        "Nome",
        "Tipo",
        "Grupo",
        "Sistema",
        "Ordem",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        self._chaves_by_row: dict[int, DefValuesetChaveResumo] = {}

        self.cabecalho = BarraCabecalho(
            "Chaves ValueSet",
            [
                "Categorias usadas para ligar peças, ferragens, materiais, acabamentos "
                "e sistemas aos ValueSets do orçamento e dos items."
            ],
        )

        self.new_button = QPushButton("Nova Chave")
        self.new_button.clicked.connect(self.abrir_nova_chave)
        self.edit_button = QPushButton("Editar Chave")
        self.edit_button.clicked.connect(self.abrir_editar_chave)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.clicked.connect(self.alternar_chave_ativa)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("defValuesetChavesStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(ESTILO_TABELA_CONFIG)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._handle_double_click)
        ligar_persistencia_larguras(self.table, "valueset_chaves")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar()

    def carregar(self) -> None:
        """Load all ValueSet keys into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                chaves = DefValuesetChaveService(session).listar_chaves()
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Nao foi possivel carregar as chaves ValueSet.", error)
            )
            return

        self._preencher(chaves)

        if not chaves:
            self.status_label.setText("Sem chaves ValueSet para mostrar.")

    def _preencher(self, chaves: list[DefValuesetChaveResumo]) -> None:
        """Fill the table with ValueSet keys."""
        self._chaves_by_row = {}
        self.table.setRowCount(len(chaves))

        tipo_anterior = object()
        indice_grupo = -1
        for row_index, chave in enumerate(chaves):
            self._chaves_by_row[row_index] = chave
            tipo_atual = chave.tipo or ""
            primeira_linha_grupo = tipo_atual != tipo_anterior
            if primeira_linha_grupo:
                indice_grupo += 1
                tipo_anterior = tipo_atual
            fundo = QBrush(QColor(cor_grupo_chave(indice_grupo)))
            values = [
                chave.codigo,
                chave.nome,
                tipo_atual if primeira_linha_grupo else "",
                (chave.grupo or "") if primeira_linha_grupo else "",
                self._format_bool(chave.sistema),
                str(chave.ordem),
                self._format_bool(chave.ativo),
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setBackground(fundo)
                font = QFont(item.font())
                if column_index == 0:
                    font.setBold(True)
                if not chave.ativo:
                    font.setItalic(True)
                    item.setForeground(QBrush(QColor(CINZA_ESCURO)))
                item.setFont(font)
                self.table.setItem(row_index, column_index, item)

    def abrir_nova_chave(self) -> None:
        """Open the dialog to create a new ValueSet key."""
        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                self._criar_chave_from_form_data(form_data)
            except IntegrityError:
                dialog.set_error("Já existe uma chave com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar a chave.", error)
                )
                return False

            saved = True
            return True

        dialog = DefValuesetChaveDialog(parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Chave ValueSet criada.")

    def abrir_editar_chave(self) -> None:
        """Open the dialog to edit the selected ValueSet key."""
        chave = self._get_selected_chave()
        if chave is None:
            self.status_label.setText("Selecione uma chave para editar.")
            return

        saved = False
        saved_as = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    DefValuesetChaveService(session).editar_chave(
                        chave.id,
                        EditarDefValuesetChaveData(
                            codigo=form_data.codigo,
                            nome=form_data.nome,
                            descricao=form_data.descricao,
                            tipo=form_data.tipo,
                            grupo=form_data.grupo,
                            sistema=form_data.sistema,
                            ativo=form_data.ativo,
                            ordem=form_data.ordem,
                            observacoes=form_data.observacoes,
                        ),
                    )
            except IntegrityError:
                dialog.set_error("Já existe uma chave com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar a chave.", error)
                )
                return False

            saved = True
            return True

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as

            try:
                self._criar_chave_from_form_data(form_data)
            except IntegrityError:
                dialog.set_error("Já existe uma chave com esse código.")
                return False
            except ValueError as error:
                dialog.set_error(self._error_message(error))
                return False
            except SQLAlchemyError as error:
                dialog.set_error(
                    mensagem_erro_bd("Não foi possível guardar a chave.", error)
                )
                return False

            saved_as = True
            return True

        dialog = DefValuesetChaveDialog(
            chave=chave,
            parent=self,
            on_save=handle_save,
            on_save_as=handle_save_as,
        )
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Chave ValueSet atualizada.")
        elif saved_as:
            self.carregar()
            self.status_label.setText("Chave ValueSet gravada como nova.")

    def alternar_chave_ativa(self) -> None:
        """Toggle the active state of the selected ValueSet key after confirmation."""
        chave = self._get_selected_chave()
        if chave is None:
            self.status_label.setText("Selecione uma chave para ativar/desativar.")
            return

        acao = "desativar" if chave.ativo else "reativar"
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} a chave {chave.codigo}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = DefValuesetChaveService(session)
                if chave.ativo:
                    service.desativar_chave(chave.id)
                else:
                    service.ativar_chave(chave.id)
        except SQLAlchemyError as error:
            self.status_label.setText(
                mensagem_erro_bd("Não foi possível atualizar o estado da chave.", error)
            )
            return

        estado = "desativada" if chave.ativo else "reativada"
        self.carregar()
        self.status_label.setText(f"Chave {estado}.")

    def _get_selected_chave(self) -> DefValuesetChaveResumo | None:
        """Return the selected ValueSet key."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._chaves_by_row.get(row)

    def _criar_chave_from_form_data(self, form_data):
        """Create a ValueSet key from dialog data."""
        with SessionLocal() as session:
            return DefValuesetChaveService(session).criar_chave(
                CriarDefValuesetChaveData(
                    codigo=form_data.codigo,
                    nome=form_data.nome,
                    descricao=form_data.descricao,
                    tipo=form_data.tipo,
                    grupo=form_data.grupo,
                    sistema=form_data.sistema,
                    ativo=form_data.ativo,
                    ordem=form_data.ordem,
                    observacoes=form_data.observacoes,
                )
            )

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Edit a ValueSet key when the user double-clicks its row."""
        self.table.selectRow(row)
        self.abrir_editar_chave()

    def _error_message(self, error: ValueError) -> str:
        """Map a service ValueError to a friendly message."""
        if "codigo ja existe" in str(error):
            return "Já existe uma chave com esse código."

        return "Não foi possível guardar a chave."

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
