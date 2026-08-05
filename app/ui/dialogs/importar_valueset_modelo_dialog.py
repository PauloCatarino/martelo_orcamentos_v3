"""Dialog for selecting a ValueSet model to import into a budget."""

from __future__ import annotations

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.core.session import app_session
from app.db.session import SessionLocal
from app.repositories.def_valueset_modelo_repository import DefValuesetModeloResumo
from app.services.def_valueset_modelo_service import DefValuesetModeloService
from app.ui.widgets.estilo_tabela_orcamentos import configurar_tabela_orcamentos
from app.ui.helpers.valueset_modelos_tabela import (
    COLUNAS_COM_DICA,
    COLUNAS_MODELO_VALUESET,
    valores_modelo_valueset,
)
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


class ImportarValuesetModeloDialog(QDialog):
    """Modal dialog to search and select an active ValueSet model.

    Models are split into two tabs: user models and global/shared models.
    """

    # As mesmas colunas da página Modelos ValueSet: quem escolhe aqui vê o
    # mesmo que viu lá.
    TABLE_HEADERS = list(COLUNAS_MODELO_VALUESET)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.selected_modelo: DefValuesetModeloResumo | None = None
        self._abas: dict[str, dict] = {}

        self.setWindowTitle("Importar Modelo ValueSet")
        self.setModal(True)
        # Largo: são oito colunas, entre elas descrição e observações.
        self.setMinimumSize(1100, 520)
        ecra = QGuiApplication.primaryScreen()
        if ecra is not None:
            disponivel = ecra.availableGeometry()
            self.resize(
                min(1500, max(1100, disponivel.width() - 200)),
                min(700, max(520, disponivel.height() - 200)),
            )

        self.status_label = QLabel("")
        self.status_label.setObjectName("importarValuesetModeloStatus")

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_aba("user"), "Utilizador")
        self.tabs.addTab(self._build_aba("global"), "Global")

        self.import_button = QPushButton("Importar")
        self.import_button.clicked.connect(self._importar)
        self.cancel_button = QPushButton("Cancelar")
        self.cancel_button.clicked.connect(self.reject)

        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.import_button)
        buttons_layout.addWidget(self.cancel_button)

        layout = QVBoxLayout()
        layout.addWidget(self.tabs, stretch=1)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons_layout)
        self.setLayout(layout)

        self._carregar()

    def _build_aba(self, key: str) -> QWidget:
        """Build one tab (search field + table) and register its state."""
        search = QLineEdit()
        search.setPlaceholderText("Pesquisar modelo...")
        search.textChanged.connect(lambda _text, aba_key=key: self._filtrar(aba_key))

        table = QTableWidget(0, len(self.TABLE_HEADERS))
        table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        # A mesma linguagem visual da página Modelos ValueSet.
        configurar_tabela_orcamentos(table, compacta=True)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        table.horizontalHeader().setStretchLastSection(False)
        # Chave nova: as larguras guardadas eram de uma tabela com 4 colunas.
        restaurou = ligar_persistencia_larguras(
            table, f"dialog_importar_valueset_{key}_v2"
        )
        table.cellDoubleClicked.connect(
            lambda row, _column, aba_key=key: self._selecionar_da_aba(aba_key, row)
        )

        container = QWidget()
        container_layout = QVBoxLayout()
        container_layout.addWidget(search)
        container_layout.addWidget(table, stretch=1)
        container.setLayout(container_layout)

        self._abas[key] = {
            "search": search,
            "table": table,
            "modelos": [],
            "by_row": {},
            # Larguras por conteúdo só quando não há nada guardado: senão
            # apagavam as que o utilizador ajustou.
            "larguras_por_conteudo": not restaurou,
        }
        return container

    def _carregar(self) -> None:
        """Load active ValueSet models: the user's own, plus the global ones.

        O separador "Utilizador" mostra **só os modelos de quem está com sessão
        iniciada** — nem os dos colegas nem os do administrador. Quem importa um
        modelo para um orçamento quer os seus; os que são para toda a gente
        estão no separador "Global". (Na página Modelos ValueSet é diferente de
        propósito: aí um administrador vê os de todos, porque é onde se gerem.)
        """
        self.status_label.clear()

        try:
            with SessionLocal() as session:
                service = DefValuesetModeloService(session)
                utilizador, globais = service.listar_modelos_para_separadores(
                    self._user_id(), is_admin=False
                )
                self._abas["user"]["modelos"] = utilizador
                self._abas["global"]["modelos"] = globais
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os modelos ValueSet.")
            return

        self._filtrar("user")
        self._filtrar("global")

    @staticmethod
    def _user_id() -> int | None:
        """Id de quem está com sessão iniciada (None sem sessão)."""
        valor = getattr(app_session.current_user, "id", None)
        return int(valor) if valor else None

    def _filtrar(self, key: str) -> None:
        """Filter one tab's models by its own search term."""
        aba = self._abas[key]
        termo = aba["search"].text().strip().lower()
        if termo:
            modelos = [
                modelo
                for modelo in aba["modelos"]
                if termo in (modelo.codigo or "").lower()
                or termo in (modelo.nome or "").lower()
                or termo in (modelo.tipo or "").lower()
                or termo in (modelo.descricao or "").lower()
            ]
        else:
            modelos = list(aba["modelos"])

        self._preencher(key, modelos)

    def _preencher(self, key: str, modelos: list[DefValuesetModeloResumo]) -> None:
        """Fill one tab's table with ValueSet models."""
        aba = self._abas[key]
        table = aba["table"]
        aba["by_row"] = {}
        table.setRowCount(len(modelos))

        for row_index, modelo in enumerate(modelos):
            aba["by_row"][row_index] = modelo
            for column_index, value in enumerate(valores_modelo_valueset(modelo)):
                item = QTableWidgetItem(value)
                if value and self.TABLE_HEADERS[column_index] in COLUNAS_COM_DICA:
                    item.setToolTip(value)
                table.setItem(row_index, column_index, item)

        if aba["larguras_por_conteudo"] and modelos:
            table.resizeColumnsToContents()
            aba["larguras_por_conteudo"] = False

    def _aba_ativa(self) -> str:
        """Return the key of the currently selected tab."""
        return "global" if self.tabs.currentIndex() == 1 else "user"

    def _get_selected(self) -> DefValuesetModeloResumo | None:
        """Return the model selected in the active tab."""
        aba = self._abas[self._aba_ativa()]
        row = aba["table"].currentRow()
        if row < 0:
            return None

        return aba["by_row"].get(row)

    def _importar(self) -> None:
        """Confirm the model selected in the active tab and close the dialog."""
        modelo = self._get_selected()
        if modelo is None:
            self.status_label.setText("Selecione um modelo.")
            return

        self.selected_modelo = modelo
        self.accept()

    def _selecionar_da_aba(self, key: str, row: int) -> None:
        """Select and accept a model when its row is double-clicked."""
        aba = self._abas[key]
        aba["table"].selectRow(row)
        modelo = aba["by_row"].get(row)
        if modelo is None:
            return

        self.selected_modelo = modelo
        self.accept()
