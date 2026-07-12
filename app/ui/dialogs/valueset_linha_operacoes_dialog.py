"""Generic dialog for managing operations of one ValueSet line."""

from __future__ import annotations

from collections.abc import Callable

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
    QVBoxLayout,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.regra_operacao_types import get_regra_operacao_label
from app.domain.operacao_acao_types import get_operacao_acao_label
from app.repositories.def_operacao_repository import DefOperacaoResumo
from app.services.def_maquina_service import DefMaquinaService
from app.services.def_operacao_service import DefOperacaoService
from app.ui.dialogs.def_peca_operacao_dialog import (
    DefPecaOperacaoDialog,
    DefPecaOperacaoDialogData,
    UNIDADE_TEMPO_LABELS,
)
from app.utils.formatters import format_quantity


ListarOperacoesCallable = Callable[[], list]
GuardarOperacaoCallable = Callable[[DefPecaOperacaoDialogData], None]
EditarOperacaoCallable = Callable[[int, DefPecaOperacaoDialogData], None]
AlternarOperacaoCallable = Callable[[object], None]


class ValuesetLinhaOperacoesDialog(QDialog):
    """Modal dialog for managing operations of a ValueSet line."""

    OPERACOES_HEADERS = [
        "Ordem",
        "Ação",
        "Operação",
        "Tipo",
        "Máquina",
        "Regra cálculo",
        "Quantidade base",
        "Construção rasgo",
        "Tempo setup",
        "Tempo por unidade",
        "Unidade tempo",
        "Obrigatório",
        "Ativo",
        "Observações",
    ]

    def __init__(
        self,
        *,
        titulo: str,
        listar_operacoes: ListarOperacoesCallable,
        criar_operacao: GuardarOperacaoCallable,
        editar_operacao: EditarOperacaoCallable,
        alternar_operacao: AlternarOperacaoCallable,
        parent=None,
        natureza_peca: str | None = None,
    ) -> None:
        super().__init__(parent)

        self._listar_operacoes = listar_operacoes
        self._criar_operacao = criar_operacao
        self._editar_operacao = editar_operacao
        self._alternar_operacao = alternar_operacao
        self._natureza_peca = natureza_peca
        self.operacoes_linha: list = []
        self._operacoes_by_row: dict[int, object] = {}
        self._operacao_resumos: dict[int, DefOperacaoResumo] = {}
        self._maquina_labels: dict[int, str] = {}
        self.alterado = False

        self.setWindowTitle(titulo)
        self.setModal(True)
        self.setMinimumSize(980, 460)

        info = QLabel(
            "Operações específicas desta variante ValueSet. Cada linha indica "
            "explicitamente se adiciona, substitui ou desativa uma operação base."
        )
        info.setWordWrap(True)

        self.nova_operacao_button = QPushButton("Nova Operação")
        self.nova_operacao_button.clicked.connect(self.abrir_nova_operacao)
        self.editar_operacao_button = QPushButton("Editar Operação")
        self.editar_operacao_button.clicked.connect(self.abrir_editar_operacao)
        self.toggle_operacao_button = QPushButton("Ativar/Desativar")
        self.toggle_operacao_button.clicked.connect(self.alternar_operacao_ativa)
        self.fechar_button = QPushButton("Fechar")
        self.fechar_button.clicked.connect(self.accept)

        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.nova_operacao_button)
        buttons_layout.addWidget(self.editar_operacao_button)
        buttons_layout.addWidget(self.toggle_operacao_button)
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.fechar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("valuesetLinhaOperacoesStatus")

        self.operacoes_table = QTableWidget(0, len(self.OPERACOES_HEADERS))
        self.operacoes_table.setHorizontalHeaderLabels(self.OPERACOES_HEADERS)
        self.operacoes_table.verticalHeader().setVisible(False)
        self.operacoes_table.setAlternatingRowColors(True)
        self.operacoes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.operacoes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.operacoes_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.operacoes_table.cellDoubleClicked.connect(
            self._handle_operacao_double_click
        )

        layout = QVBoxLayout()
        layout.addWidget(info)
        layout.addLayout(buttons_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.operacoes_table, stretch=1)
        self.setLayout(layout)

        self.recarregar_operacoes()

    def recarregar_operacoes(self) -> None:
        """Reload operation links and operation/machine labels."""
        try:
            self.operacoes_linha = self._listar_operacoes()
            with SessionLocal() as session:
                all_operacoes = DefOperacaoService(session).listar_operacoes()
                all_maquinas = DefMaquinaService(session).listar_maquinas()
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar as operações.")
            return

        self._operacao_resumos = {operacao.id: operacao for operacao in all_operacoes}
        self._maquina_labels = {
            maquina.id: f"{maquina.codigo} - {maquina.nome}" for maquina in all_maquinas
        }
        self._preencher_operacoes()

    def _preencher_operacoes(self) -> None:
        """Fill the operations table from current read models."""
        self._operacoes_by_row = {}
        self.operacoes_table.setRowCount(len(self.operacoes_linha))

        for row_index, ligacao in enumerate(self.operacoes_linha):
            self._operacoes_by_row[row_index] = ligacao
            operacao = self._operacao_resumos.get(ligacao.def_operacao_id)
            values = [
                str(ligacao.ordem),
                get_operacao_acao_label(getattr(ligacao, "acao", None)),
                self._format_operacao_label(ligacao.def_operacao_id, operacao),
                (operacao.tipo_operacao or "") if operacao is not None else "",
                self._format_operacao_maquina(operacao),
                get_regra_operacao_label(ligacao.regra_calculo),
                format_quantity(ligacao.quantidade_base),
                (
                    f"{getattr(ligacao, 'rasgo_qt_comp', 0)} × COMP + "
                    f"{getattr(ligacao, 'rasgo_qt_larg', 0)} × LARG"
                    if getattr(ligacao, "rasgo_qt_comp", 0) or getattr(ligacao, "rasgo_qt_larg", 0)
                    else ""
                ),
                format_quantity(ligacao.tempo_setup_minutos),
                format_quantity(ligacao.tempo_por_unidade_minutos),
                UNIDADE_TEMPO_LABELS.get(
                    ligacao.unidade_tempo,
                    ligacao.unidade_tempo or "",
                ),
                self._format_bool(ligacao.obrigatorio),
                self._format_bool(ligacao.ativo),
                ligacao.observacoes or "",
            ]

            for column_index, value in enumerate(values):
                self.operacoes_table.setItem(
                    row_index, column_index, QTableWidgetItem(value)
                )

        self.status_label.setText(self._operacoes_status_text())

    def _operacoes_status_text(self) -> str:
        if not self.operacoes_linha:
            return "Sem operações. Use 'Nova Operação' para adicionar."
        return ""

    def abrir_nova_operacao(self) -> None:
        """Open the operation dialog to create a new link."""
        operacoes = self._carregar_operacoes_disponiveis()
        if operacoes is None:
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved
            try:
                self._criar_operacao(form_data)
            except (SQLAlchemyError, ValueError) as error:
                dialog.set_error(self._operacao_error_message(error))
                return False
            saved = True
            return True

        dialog = DefPecaOperacaoDialog(
            operacoes,
            parent=self,
            on_save=handle_save,
            mostrar_acao=True,
            natureza_peca=self._natureza_peca,
        )
        if dialog.exec() and saved:
            self.alterado = True
            self.recarregar_operacoes()
            self.status_label.setText("Operação associada.")

    def abrir_editar_operacao(self) -> None:
        """Open the operation dialog to edit the selected link."""
        ligacao = self._get_selected_operacao()
        if ligacao is None:
            self.status_label.setText("Selecione uma operação para editar.")
            return

        operacoes = self._carregar_operacoes_disponiveis(ligacao)
        if operacoes is None:
            return

        saved = False

        def handle_save(form_data) -> bool:
            nonlocal saved
            try:
                self._editar_operacao(ligacao.id, form_data)
            except (SQLAlchemyError, ValueError) as error:
                dialog.set_error(self._operacao_error_message(error))
                return False
            saved = True
            return True

        dialog = DefPecaOperacaoDialog(
            operacoes,
            ligacao=ligacao,
            parent=self,
            on_save=handle_save,
            mostrar_acao=True,
            natureza_peca=self._natureza_peca,
        )
        if dialog.exec() and saved:
            self.alterado = True
            self.recarregar_operacoes()
            self.status_label.setText("Operação atualizada.")

    def alternar_operacao_ativa(self) -> None:
        """Toggle the active state of the selected operation link."""
        ligacao = self._get_selected_operacao()
        if ligacao is None:
            self.status_label.setText("Selecione uma operação para ativar/desativar.")
            return

        acao = "desativar" if ligacao.ativo else "reativar"
        confirm = QMessageBox.question(
            self,
            "Confirmar",
            f"Deseja {acao} esta operação associada?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            self._alternar_operacao(ligacao)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Não foi possível atualizar o estado da operação.")
            return

        estado = "desativada" if ligacao.ativo else "reativada"
        self.alterado = True
        self.recarregar_operacoes()
        self.status_label.setText(f"Operação {estado}.")

    def _get_selected_operacao(self):
        row = self.operacoes_table.currentRow()
        if row < 0:
            return None
        return self._operacoes_by_row.get(row)

    def _handle_operacao_double_click(self, row: int, _column: int) -> None:
        self.operacoes_table.selectRow(row)
        self.abrir_editar_operacao()

    def _carregar_operacoes_disponiveis(self, ligacao=None) -> list[DefOperacaoResumo] | None:
        """Return active operations for the combo, keeping the current one if inactive."""
        try:
            with SessionLocal() as session:
                service = DefOperacaoService(session)
                operacoes = service.listar_operacoes_ativas()
                atual = None
                if ligacao is not None:
                    if not any(op.id == ligacao.def_operacao_id for op in operacoes):
                        atual = service.obter_por_id(ligacao.def_operacao_id)
        except SQLAlchemyError:
            self.status_label.setText("Não foi possível carregar as operações.")
            return None

        if atual is not None:
            return [atual, *operacoes]
        return operacoes

    def _format_operacao_label(
        self, operacao_id: int, operacao: DefOperacaoResumo | None
    ) -> str:
        if operacao is not None:
            return f"{operacao.codigo} - {operacao.nome}"
        return f"#{operacao_id}"

    def _format_operacao_maquina(self, operacao: DefOperacaoResumo | None) -> str:
        if operacao is None or operacao.maquina_id is None:
            return ""
        return self._maquina_labels.get(operacao.maquina_id, f"#{operacao.maquina_id}")

    def _operacao_error_message(self, error: Exception) -> str:
        if "associada" in str(error).lower():
            return "Esta operação já está associada a esta linha."
        return "Não foi possível guardar a operação."

    def _format_bool(self, value: bool) -> str:
        return "Sim" if value else "Não"
