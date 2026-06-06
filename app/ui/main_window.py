"""Main application window for Martelo Orcamentos V3."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.models import User
from app.repositories.orcamento_repository import OrcamentoResumo
from app.ui.pages import (
    CaminhosSistemaPage,
    ConfiguracoesPage,
    DefPecasPage,
    MateriasPrimasPage,
    OrcamentoDetailPage,
    OrcamentosPage,
)


class MainWindow(QMainWindow):
    """Application shell window."""

    logout_requested = Signal()

    def __init__(self, authenticated_user: User | None = None) -> None:
        super().__init__()

        self.authenticated_user = authenticated_user

        self.setWindowTitle("Martelo Or\u00e7amentos V3")
        self.resize(1100, 720)

        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        title = QLabel("Martelo Or\u00e7amentos V3")
        title.setObjectName("mainTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        user_label = QLabel(self._format_user_info())
        user_label.setObjectName("authenticatedUserInfo")
        user_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        logout_button = QPushButton("Sair")
        logout_button.setObjectName("logoutButton")
        logout_button.clicked.connect(self.request_logout)

        header_layout.addWidget(title, stretch=1)
        header_layout.addWidget(user_label, stretch=1)
        header_layout.addWidget(logout_button)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.Shape.StyledPanel)
        sidebar.setFixedWidth(180)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        inicio_button = QPushButton("In\u00edcio")
        inicio_button.clicked.connect(lambda: self.show_page("inicio"))

        orcamentos_button = QPushButton("Or\u00e7amentos")
        orcamentos_button.clicked.connect(lambda: self.show_page("orcamentos"))

        clientes_button = QPushButton("Clientes")
        clientes_button.clicked.connect(lambda: self.show_page("clientes"))

        configuracoes_button = QPushButton("Configura\u00e7\u00f5es")
        configuracoes_button.clicked.connect(lambda: self.show_page("configuracoes"))

        for button in (inicio_button, orcamentos_button, clientes_button, configuracoes_button):
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()
        sidebar.setLayout(sidebar_layout)

        self.pages = QStackedWidget()
        self._page_indexes: dict[str, int] = {}
        self._pages_by_name: dict[str, QWidget] = {}
        self.orcamentos_page = OrcamentosPage(on_open_orcamento=self.open_orcamento_detail)
        self.def_pecas_page = DefPecasPage()
        self.materias_primas_page = MateriasPrimasPage()
        self.caminhos_sistema_page = CaminhosSistemaPage()
        self.configuracoes_page = ConfiguracoesPage(
            on_open_def_pecas=lambda: self.show_page("pecas"),
            on_open_materias_primas=lambda: self.show_page("materias_primas"),
            on_open_caminhos_sistema=lambda: self.show_page("caminhos_sistema"),
        )
        self._add_page("inicio", self._create_text_page("Bem-vindo ao Martelo Or\u00e7amentos V3"))
        self._add_page("orcamentos", self.orcamentos_page)
        self._add_page("pecas", self.def_pecas_page)
        self._add_page("materias_primas", self.materias_primas_page)
        self._add_page("caminhos_sistema", self.caminhos_sistema_page)
        self._add_page("clientes", self._create_text_page("Clientes"))
        self._add_page("configuracoes", self.configuracoes_page)

        content_layout.addWidget(sidebar)
        content_layout.addWidget(self.pages, stretch=1)

        main_layout.addLayout(header_layout)
        main_layout.addLayout(content_layout, stretch=1)

        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def _format_user_info(self) -> str:
        """Return display text for the authenticated user."""
        if self.authenticated_user is None:
            return "Utilizador: n/a"

        return (
            f"{self.authenticated_user.nome}\n"
            f"@{self.authenticated_user.username} | {self.authenticated_user.role}"
        )

    def request_logout(self) -> None:
        """Emit a logout request."""
        self.logout_requested.emit()

    def _add_page(self, name: str, page: QWidget) -> None:
        """Add a page to the central workspace."""
        self._pages_by_name[name] = page
        self._page_indexes[name] = self.pages.addWidget(page)

    def show_page(self, name: str) -> None:
        """Show one central workspace page."""
        page_index = self._page_indexes[name]
        self.pages.setCurrentIndex(page_index)

    def open_orcamento_detail(self, orcamento: OrcamentoResumo) -> None:
        """Open the detail page for a selected budget."""
        detail_page = OrcamentoDetailPage(orcamento, on_back=lambda: self.show_page("orcamentos"))
        self._replace_page("orcamento_detail", detail_page)
        self.show_page("orcamento_detail")

    def _replace_page(self, name: str, page: QWidget) -> None:
        """Replace a named page in the central workspace."""
        old_page = self._pages_by_name.get(name)
        if old_page is not None:
            self.pages.removeWidget(old_page)
            old_page.deleteLater()

        self._pages_by_name[name] = page
        self.pages.addWidget(page)
        self._rebuild_page_indexes()

    def _rebuild_page_indexes(self) -> None:
        """Rebuild page indexes after adding or removing widgets."""
        self._page_indexes = {
            name: self.pages.indexOf(page)
            for name, page in self._pages_by_name.items()
        }

    def _create_text_page(self, text: str) -> QWidget:
        """Create a simple placeholder page."""
        page = QFrame()
        page.setFrameShape(QFrame.Shape.StyledPanel)

        layout = QVBoxLayout()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        page.setLayout(layout)

        return page
