"""Detail page for one ValueSet model and its lines."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QFormLayout,
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
from app.domain.numeros import formatar_percentagem
from app.repositories.def_valueset_modelo_linha_repository import DefValuesetModeloLinhaResumo
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services.def_valueset_modelo_linha_service import (
    CriarDefValuesetModeloLinhaData,
    DefValuesetModeloLinhaService,
    EditarDefValuesetModeloLinhaData,
)
from app.ui.dialogs.def_valueset_modelo_linha_dialog import DefValuesetModeloLinhaDialog
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency


class DefValuesetModeloDetailPage(QWidget):
    """Detail page showing one ValueSet model and managing its lines."""

    LINHA_HEADERS = [
        "Chave",
        "Opção",
        "Nome opção",
        "Ref LE",
        "Descrição orçamento",
        "Unidade",
        "Preço tabela",
        "Margem %",
        "Desconto %",
        "Preço líquido",
        "Desp %",
        "Tipo",
        "Família",
        "Padrão",
        "Ordem",
        "Editado localmente",
        "Ativo",
    ]

    def __init__(
        self,
        modelo: DefValuesetModeloResumo,
        on_back: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        self.modelo = modelo
        self.on_back = on_back
        self._linhas_by_row: dict[int, DefValuesetModeloLinhaResumo] = {}

        self.cabecalho = BarraCabecalho(
            f"Modelo ValueSet: {modelo.nome}",
            [f"Configurações > Modelos ValueSet > {modelo.nome}"],
        )

        form = QFormLayout()
        for label, value in [
            ("Código", modelo.codigo),
            ("Nome", modelo.nome),
            ("Tipo", modelo.tipo or ""),
            ("Âmbito", modelo.ambito),
            ("Ativo", self._format_bool(modelo.ativo)),
        ]:
            form.addRow(f"{label}:", QLabel(value))

        self.new_button = QPushButton("Nova Linha")
        self.new_button.clicked.connect(self.abrir_nova_linha)
        self.edit_button = QPushButton("Editar Linha")
        self.edit_button.clicked.connect(self.abrir_editar_linha)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.clicked.connect(self.alternar_linha_ativa)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_linhas)
        self.back_button = QPushButton("Voltar à lista")
        self.back_button.clicked.connect(self._handle_back)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.new_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.back_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("defValuesetModeloDetailStatus")

        self.table = QTableWidget(0, len(self.LINHA_HEADERS))
        self.table.setHorizontalHeaderLabels(self.LINHA_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._handle_double_click)
        ligar_persistencia_larguras(self.table, "valueset_modelo_detail")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(form)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_linhas()

    def carregar_linhas(self) -> None:
        """Load the model lines into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                linhas = DefValuesetModeloLinhaService(session).listar_linhas_do_modelo(
                    self.modelo.id
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as linhas do modelo.")
            return

        self._preencher(linhas)

        if not linhas:
            self.status_label.setText("Sem linhas neste modelo.")

    def _preencher(self, linhas: list[DefValuesetModeloLinhaResumo]) -> None:
        """Fill the table with model lines."""
        self._linhas_by_row = {}
        self.table.setRowCount(len(linhas))

        for row_index, linha in enumerate(linhas):
            self._linhas_by_row[row_index] = linha
            values = [
                linha.chave,
                linha.codigo_opcao or "",
                linha.nome_opcao or "",
                linha.ref_le or "",
                linha.descricao_no_orcamento or "",
                linha.unidade or "",
                format_currency(linha.preco_tabela),
                formatar_percentagem(linha.margem_percentagem),
                formatar_percentagem(linha.desconto_percentagem),
                format_currency(linha.preco_liquido),
                formatar_percentagem(linha.desperdicio_percentagem),
                linha.tipo_materia_prima or "",
                linha.familia_materia_prima or "",
                self._format_bool(linha.padrao),
                str(linha.ordem),
                self._format_bool(linha.editado_localmente),
                self._format_bool(linha.ativo),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def abrir_nova_linha(self) -> None:
        """Open the dialog to create a new model line."""
        self._abrir_dialog_criar_linha(success_message="Linha criada.")

    def _abrir_dialog_criar_linha(
        self,
        *,
        success_message: str,
    ) -> None:
        """Open a create dialog for a model line."""
        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                self._criar_linha_from_form_data(form_data)
            except (IntegrityError, ValueError) as error:
                dialog.set_error(self._linha_error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar a linha.")
                return False

            saved = True
            return True

        dialog = DefValuesetModeloLinhaDialog(parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar_linhas()
            self.status_label.setText(success_message)

    def _criar_linha_from_form_data(self, form_data):
        """Create one model line from dialog data."""
        with SessionLocal() as session:
            service = DefValuesetModeloLinhaService(session)
            result = service.criar_linha(
                CriarDefValuesetModeloLinhaData(
                    def_valueset_modelo_id=self.modelo.id,
                    chave=form_data.chave,
                    codigo_opcao=form_data.codigo_opcao,
                    nome_opcao=form_data.nome_opcao,
                    ref_materia_prima=form_data.ref_materia_prima,
                    descricao_materia_prima=form_data.descricao_materia_prima,
                    valor_texto=form_data.valor_texto,
                    padrao=False,
                    ordem=form_data.ordem,
                    observacoes=form_data.observacoes,
                    ativo=form_data.ativo,
                    ref_le=form_data.ref_le,
                    descricao_no_orcamento=form_data.descricao_no_orcamento,
                    preco_tabela=form_data.preco_tabela,
                    margem_percentagem=form_data.margem_percentagem,
                    desconto_percentagem=form_data.desconto_percentagem,
                    preco_liquido=form_data.preco_liquido,
                    unidade=form_data.unidade,
                    desperdicio_percentagem=form_data.desperdicio_percentagem,
                    tipo_materia_prima=form_data.tipo_materia_prima,
                    familia_materia_prima=form_data.familia_materia_prima,
                    coresp_orla_0_4=form_data.coresp_orla_0_4,
                    coresp_orla_1_0=form_data.coresp_orla_1_0,
                    comp_mp=form_data.comp_mp,
                    larg_mp=form_data.larg_mp,
                    esp_mp=form_data.esp_mp,
                    origem_dados=form_data.origem_dados,
                    editado_localmente=form_data.editado_localmente,
                )
            )
            if form_data.padrao:
                service.definir_como_padrao(result.id)

            return result

    def abrir_editar_linha(self) -> None:
        """Open the dialog to edit the selected model line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para editar.")
            return

        saved = False
        saved_as = False

        def handle_save(form_data) -> bool:
            nonlocal saved

            try:
                with SessionLocal() as session:
                    service = DefValuesetModeloLinhaService(session)
                    service.editar_linha(
                        linha.id,
                        EditarDefValuesetModeloLinhaData(
                            def_valueset_modelo_id=self.modelo.id,
                            chave=form_data.chave,
                            codigo_opcao=form_data.codigo_opcao,
                            nome_opcao=form_data.nome_opcao,
                            ref_materia_prima=form_data.ref_materia_prima,
                            descricao_materia_prima=form_data.descricao_materia_prima,
                            valor_texto=form_data.valor_texto,
                            padrao=False,
                            ordem=form_data.ordem,
                            observacoes=form_data.observacoes,
                            ativo=form_data.ativo,
                            ref_le=form_data.ref_le,
                            descricao_no_orcamento=form_data.descricao_no_orcamento,
                            preco_tabela=form_data.preco_tabela,
                            margem_percentagem=form_data.margem_percentagem,
                            desconto_percentagem=form_data.desconto_percentagem,
                            preco_liquido=form_data.preco_liquido,
                            unidade=form_data.unidade,
                            desperdicio_percentagem=form_data.desperdicio_percentagem,
                            tipo_materia_prima=form_data.tipo_materia_prima,
                            familia_materia_prima=form_data.familia_materia_prima,
                            coresp_orla_0_4=form_data.coresp_orla_0_4,
                            coresp_orla_1_0=form_data.coresp_orla_1_0,
                            comp_mp=form_data.comp_mp,
                            larg_mp=form_data.larg_mp,
                            esp_mp=form_data.esp_mp,
                            origem_dados=form_data.origem_dados,
                            editado_localmente=form_data.editado_localmente,
                        ),
                    )
                    if form_data.padrao:
                        service.definir_como_padrao(linha.id)
            except (IntegrityError, ValueError) as error:
                dialog.set_error(self._linha_error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar a linha.")
                return False

            saved = True
            return True

        def handle_save_as(form_data) -> bool:
            nonlocal saved_as

            try:
                self._criar_linha_from_form_data(form_data)
            except (IntegrityError, ValueError) as error:
                dialog.set_error(self._linha_error_message(error))
                return False
            except SQLAlchemyError:
                dialog.set_error("Não foi possível guardar a linha.")
                return False

            saved_as = True
            return True

        dialog = DefValuesetModeloLinhaDialog(
            linha=linha,
            parent=self,
            on_save=handle_save,
            on_save_as=handle_save_as,
        )
        if dialog.exec() and saved:
            self.carregar_linhas()
            self.status_label.setText("Linha atualizada.")
        elif saved_as:
            self.carregar_linhas()
            self.status_label.setText("Linha gravada como nova opção.")

    def alternar_linha_ativa(self) -> None:
        """Toggle the active state of the selected model line after confirmation."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para ativar/desativar.")
            return

        acao = "desativar" if linha.ativo else "reativar"
        aviso = ""
        if linha.ativo and linha.padrao:
            aviso = " A chave podera ficar sem opcao padrao."
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} esta linha?{aviso}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = DefValuesetModeloLinhaService(session)
                if linha.ativo:
                    service.desativar_linha(linha.id)
                else:
                    service.ativar_linha(linha.id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível atualizar o estado da linha.")
            return

        estado = "desativada" if linha.ativo else "reativada"
        self.carregar_linhas()
        self.status_label.setText(f"Linha {estado}.")

    def _get_selected_linha(self) -> DefValuesetModeloLinhaResumo | None:
        """Return the selected model line."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._linhas_by_row.get(row)

    def _handle_double_click(self, row: int, _column: int) -> None:
        """Edit a line when the user double-clicks its row."""
        self.table.selectRow(row)
        self.abrir_editar_linha()

    def _handle_back(self) -> None:
        """Return to the model list."""
        if self.on_back is not None:
            self.on_back()

    def _linha_error_message(self, error: Exception) -> str:
        """Map a service error to a friendly message."""
        if "opcao ja existe" in str(error):
            return "Já existe uma opção com esse código nesta chave."

        return "Não foi possível guardar a linha. Verifique a chave e o código da opção."

    def _format_materia_prima(self, linha: DefValuesetModeloLinhaResumo) -> str:
        """Format the materia-prima / value cell."""
        return (
            linha.ref_materia_prima
            or linha.descricao_materia_prima
            or linha.valor_texto
            or ""
        )

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
