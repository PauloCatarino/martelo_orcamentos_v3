"""Budget ValueSet page (import model + list lines)."""

from __future__ import annotations

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
from app.domain.numeros import formatar_percentagem
from app.repositories.orcamento_valueset_linha_repository import OrcamentoValuesetLinhaResumo
from app.services.orcamento_valueset_linha_service import (
    EditarOrcamentoValuesetLinhaData,
    OrcamentoValuesetLinhaService,
)
from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog
from app.ui.dialogs.orcamento_valueset_linha_dialog import OrcamentoValuesetLinhaDialog
from app.utils.formatters import format_currency, format_quantity


class OrcamentoValuesetPage(QWidget):
    """Page listing the ValueSet lines of a budget version."""

    TABLE_HEADERS = [
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
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Padrão",
        "Ordem",
        "Origem",
        "Editado localmente",
        "Ativo",
    ]

    def __init__(self, orcamento_versao_id: int) -> None:
        super().__init__()

        self.orcamento_versao_id = orcamento_versao_id
        self._linhas_by_row: dict[int, OrcamentoValuesetLinhaResumo] = {}

        title = QLabel("ValueSet do Orçamento")
        title.setObjectName("pageTitle")

        info = QLabel(
            "Materiais, ferragens, acabamentos, orlas, sistemas e acessórios "
            "definidos por defeito para este orçamento."
        )
        info.setObjectName("pageSubtitle")
        info.setWordWrap(True)

        self.import_button = QPushButton("Importar Modelo")
        self.import_button.clicked.connect(self.importar_modelo)
        self.edit_button = QPushButton("Editar Linha")
        self.edit_button.clicked.connect(self.abrir_editar_linha)
        self.toggle_button = QPushButton("Ativar/Desativar")
        self.toggle_button.clicked.connect(self.alternar_linha_ativa)
        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar)

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.import_button)
        actions_layout.addWidget(self.edit_button)
        actions_layout.addWidget(self.toggle_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()

        self.status_label = QLabel("")
        self.status_label.setObjectName("orcamentoValuesetStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.cellDoubleClicked.connect(self._handle_double_click)

        layout = QVBoxLayout()
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        layout.addWidget(title)
        layout.addWidget(info)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar()

    def carregar(self) -> None:
        """Load the ValueSet lines of the budget version."""
        self.table.setRowCount(0)
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                linhas = OrcamentoValuesetLinhaService(session).listar_linhas_da_versao(
                    self.orcamento_versao_id
                )
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar o ValueSet do orcamento.")
            return

        self._preencher(linhas)

        if not linhas:
            self.status_label.setText(
                "Sem ValueSet. Use 'Importar Modelo' para preencher este orçamento."
            )

    def _preencher(self, linhas: list[OrcamentoValuesetLinhaResumo]) -> None:
        """Fill the table with ValueSet lines."""
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
                linha.coresp_orla_0_4 or "",
                linha.coresp_orla_1_0 or "",
                format_quantity(linha.comp_mp),
                format_quantity(linha.larg_mp),
                format_quantity(linha.esp_mp),
                self._format_bool(linha.padrao),
                str(linha.ordem),
                linha.origem_modelo_codigo or linha.origem_dados or "",
                self._format_bool(linha.editado_localmente),
                self._format_bool(linha.ativo),
            ]

            for column_index, value in enumerate(values):
                self.table.setItem(row_index, column_index, QTableWidgetItem(value))

    def importar_modelo(self) -> None:
        """Open the model picker and import the selected model."""
        dialog = ImportarValuesetModeloDialog(parent=self)
        if not dialog.exec() or dialog.selected_modelo is None:
            return

        modelo = dialog.selected_modelo

        try:
            with SessionLocal() as session:
                result = OrcamentoValuesetLinhaService(session).importar_modelo_para_orcamento(
                    self.orcamento_versao_id, modelo.id
                )
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível importar o modelo.")
            return

        self.carregar()
        self.status_label.setText(
            f"Modelo {result.modelo_codigo} importado: "
            f"{result.criadas} criadas, {result.atualizadas} atualizadas, "
            f"{result.ignoradas} ignoradas (editadas localmente)."
        )

    def alternar_linha_ativa(self) -> None:
        """Toggle the active state of the selected line after confirmation."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para ativar/desativar.")
            return

        acao = "desativar" if linha.ativo else "reativar"
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} esta linha do ValueSet?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            with SessionLocal() as session:
                service = OrcamentoValuesetLinhaService(session)
                if linha.ativo:
                    service.desativar_linha(linha.id)
                else:
                    service.ativar_linha(linha.id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível atualizar o estado da linha.")
            return

        estado = "desativada" if linha.ativo else "reativada"
        self.carregar()
        self.status_label.setText(f"Linha {estado}.")

    def abrir_editar_linha(self) -> None:
        """Open the edit dialog for the selected ValueSet line."""
        linha = self._get_selected_linha()
        if linha is None:
            self.status_label.setText("Selecione uma linha para editar.")
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved
            try:
                with SessionLocal() as session:
                    OrcamentoValuesetLinhaService(session).editar_linha(
                        linha.id,
                        EditarOrcamentoValuesetLinhaData(
                            orcamento_versao_id=self.orcamento_versao_id,
                            chave=form_data.chave or linha.chave,
                            codigo_opcao=form_data.codigo_opcao,
                            nome_opcao=form_data.nome_opcao,
                            descricao=linha.descricao,
                            materia_prima_id=linha.materia_prima_id,
                            ref_materia_prima=form_data.ref_materia_prima,
                            descricao_materia_prima=form_data.descricao_materia_prima,
                            valor_texto=form_data.valor_texto,
                            origem=linha.origem,
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
                            origem_modelo_id=linha.origem_modelo_id,
                            origem_modelo_codigo=linha.origem_modelo_codigo,
                            editado_localmente=form_data.editado_localmente,
                            padrao=form_data.padrao,
                            ordem=form_data.ordem,
                            observacoes=form_data.observacoes,
                            ativo=form_data.ativo,
                        ),
                    )
            except (IntegrityError, ValueError):
                dialog.set_error("Não foi possível guardar a linha. Verifique os dados.")
                return False

            saved = True
            return True

        dialog = OrcamentoValuesetLinhaDialog(linha, parent=self, on_save=handle_save)
        if dialog.exec() and saved:
            self.carregar()
            self.status_label.setText("Linha ValueSet atualizada.")

    def _handle_double_click(self, _row: int, _column: int) -> None:
        """Edit a line when the user double-clicks its row."""
        self.abrir_editar_linha()

    def _get_selected_linha(self) -> OrcamentoValuesetLinhaResumo | None:
        """Return the selected ValueSet line."""
        row = self.table.currentRow()
        if row < 0:
            return None

        return self._linhas_by_row.get(row)

    def _format_bool(self, value: bool) -> str:
        """Format a boolean for display."""
        return "Sim" if value else "Não"
