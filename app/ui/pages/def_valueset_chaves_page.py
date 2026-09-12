"""Page for managing configurable ValueSet keys."""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor, QFont
from PySide6.QtWidgets import (
    QCheckBox,
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
from app.services.def_valueset_chave_renomeacao_service import (
    DefValuesetChaveRenomeacaoService,
)
from app.ui.dialogs.def_valueset_chave_dialog import DefValuesetChaveDialog
from app.ui.dialogs.renomear_chave_valueset_dialog import (
    RenomearChaveValuesetDialog,
)
from app.ui.helpers.erros import mensagem_erro_bd
from app.ui.tema import (
    CINZA_ESCURO,
    ESTILO_TABELA_CONFIG,
    cor_grupo_chave,
)
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.ui.icones import decorar_barra, icone


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

    def __init__(self, on_back=None) -> None:
        super().__init__()

        self.on_back = on_back
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
        self.mostrar_inativas_check = QCheckBox("Mostrar inativas")
        self.mostrar_inativas_check.stateChanged.connect(lambda _=0: self.carregar())
        self.voltar_button = QPushButton("Voltar às Configurações")
        self.voltar_button.setIcon(icone("acao_voltar"))
        self.voltar_button.setToolTip("Regressar ao menu Configurações.")
        self.voltar_button.clicked.connect(
            lambda: self.on_back() if self.on_back else None
        )

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.mostrar_inativas_check)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()
        # Os icones vem do TEXTO de cada botao (ver app/ui/icones.py): a
        # mesma acao fica com a mesma cara em todas as paginas.
        decorar_barra(actions_layout)
        actions_layout.addWidget(self.voltar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("defValuesetChavesStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        self.table.setStyleSheet(ESTILO_TABELA_CONFIG)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setStretchLastSection(False)
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

        if not self.mostrar_inativas_check.isChecked():
            chaves = [chave for chave in chaves if chave.ativo]

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
        mensagem_renomeacao = ""

        def handle_save(form_data) -> bool:
            nonlocal saved, mensagem_renomeacao

            # Mudar o código é uma renomeação, não uma edição: o código está
            # escrito como texto em sete tabelas e quem ficar com o antigo
            # cala-se. Antes de gravar, mostra-se quem usa e pergunta-se o
            # alcance.
            if self._codigo_mudou(chave.codigo, form_data.codigo):
                resultado = self._renomear_chave(chave, form_data.codigo, dialog)
                if resultado is None:
                    return False
                mensagem_renomeacao = self._mensagem_renomeacao(resultado)

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
            self.status_label.setText(
                mensagem_renomeacao or "Chave ValueSet atualizada."
            )
        elif saved_as:
            self.carregar()
            self.status_label.setText("Chave ValueSet gravada como nova.")

    @staticmethod
    def _codigo_mudou(codigo_atual: str | None, codigo_novo: str | None) -> bool:
        """Diz se o código foi mesmo alterado (sem contar espaços nem caixa)."""
        return (
            DefValuesetChaveRenomeacaoService._normalizar(codigo_novo)
            != DefValuesetChaveRenomeacaoService._normalizar(codigo_atual)
        )

    def _renomear_chave(self, chave, codigo_novo: str, dialog):
        """Mostrar quem usa a chave, pedir o alcance e propagar.

        Devolve o resultado, ou ``None`` se o utilizador desistiu ou algo
        correu mal — nesse caso o diálogo de edição fica aberto com o erro.
        """
        try:
            with SessionLocal() as session:
                ocorrencias = DefValuesetChaveRenomeacaoService(
                    session
                ).contar_utilizacoes(chave.codigo)
        except SQLAlchemyError as error:
            dialog.set_error(
                mensagem_erro_bd("Não foi possível ver quem usa esta chave.", error)
            )
            return None

        codigo_limpo = DefValuesetChaveRenomeacaoService._normalizar(codigo_novo)
        confirmacao = RenomearChaveValuesetDialog(
            ocorrencias, codigo_limpo, parent=self
        )
        if not confirmacao.exec():
            dialog.set_error("Renomeação cancelada; nada foi alterado.")
            return None

        try:
            with SessionLocal() as session:
                return DefValuesetChaveRenomeacaoService(session).renomear(
                    chave.id,
                    codigo_limpo,
                    incluir_orcamentos=confirmacao.incluir_orcamentos,
                )
        except ValueError as error:
            dialog.set_error(self._error_message(error))
            return None
        except SQLAlchemyError as error:
            dialog.set_error(
                mensagem_erro_bd("Não foi possível renomear a chave.", error)
            )
            return None

    @staticmethod
    def _mensagem_renomeacao(resultado) -> str:
        """Contar ao utilizador o que a renomeação mudou, em número de linhas."""
        mensagem = (
            f"Chave {resultado.codigo_antigo} renomeada para "
            f"{resultado.codigo_novo}: {resultado.catalogos_atualizados} "
            "linha(s) de catálogo atualizadas"
        )
        if resultado.incluiu_orcamentos:
            return (
                f"{mensagem} e {resultado.orcamentos_atualizados} de orçamentos "
                "já feitos."
            )
        return f"{mensagem}. Os orçamentos já feitos ficaram como estavam."

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
