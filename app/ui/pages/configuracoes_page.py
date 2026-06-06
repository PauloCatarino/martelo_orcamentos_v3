"""Technical settings page."""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ConfiguracoesPage(QWidget):
    """Technical administration shortcuts page."""

    TECHNICAL_AREAS = [
        "Defini\u00e7\u00f5es de Pe\u00e7as",
        "Mat\u00e9rias-Primas",
        "Caminhos do Sistema",
        "Materiais",
        "Ferragens",
        "Opera\u00e7\u00f5es / M\u00e1quinas",
        "Regras de Custeio",
    ]

    def __init__(
        self,
        on_open_def_pecas: Callable[[], None] | None = None,
        on_open_materias_primas: Callable[[], None] | None = None,
        on_open_caminhos_sistema: Callable[[], None] | None = None,
        on_open_operacoes_maquinas: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()

        self.on_open_def_pecas = on_open_def_pecas
        self.on_open_materias_primas = on_open_materias_primas
        self.on_open_caminhos_sistema = on_open_caminhos_sistema
        self.on_open_operacoes_maquinas = on_open_operacoes_maquinas

        title = QLabel("Configura\u00e7\u00f5es")
        title.setObjectName("pageTitle")

        info = QLabel(
            "\u00c1rea de administra\u00e7\u00e3o t\u00e9cnica do Martelo Or\u00e7amentos V3. "
            "Aqui ser\u00e3o configuradas pe\u00e7as, materiais, ferragens, opera\u00e7\u00f5es, "
            "regras de custeio e outras tabelas de apoio."
        )
        info.setObjectName("pageSubtitle")
        info.setWordWrap(True)

        self.status_label = QLabel("")
        self.status_label.setObjectName("configuracoesStatus")

        self.def_pecas_button = QPushButton("Defini\u00e7\u00f5es de Pe\u00e7as")
        self.def_pecas_button.clicked.connect(self._open_def_pecas)

        self.materias_primas_button = QPushButton("Mat\u00e9rias-Primas")
        self.materias_primas_button.clicked.connect(self._open_materias_primas)

        self.caminhos_sistema_button = QPushButton("Caminhos do Sistema")
        self.caminhos_sistema_button.clicked.connect(self._open_caminhos_sistema)

        materiais_button = QPushButton("Materiais")
        materiais_button.clicked.connect(self._show_future_message)

        ferragens_button = QPushButton("Ferragens")
        ferragens_button.clicked.connect(self._show_future_message)

        self.operacoes_maquinas_button = QPushButton("Opera\u00e7\u00f5es / M\u00e1quinas")
        self.operacoes_maquinas_button.clicked.connect(self._open_operacoes_maquinas)

        regras_button = QPushButton("Regras de Custeio")
        regras_button.clicked.connect(self._show_future_message)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(info)
        layout.addSpacing(8)
        layout.addWidget(self.def_pecas_button)
        layout.addWidget(self.materias_primas_button)
        layout.addWidget(self.caminhos_sistema_button)
        layout.addWidget(materiais_button)
        layout.addWidget(ferragens_button)
        layout.addWidget(self.operacoes_maquinas_button)
        layout.addWidget(regras_button)
        layout.addWidget(self.status_label)
        layout.addStretch()

        self.setLayout(layout)

    def _open_def_pecas(self) -> None:
        """Open the piece definitions page through the optional callback."""
        if self.on_open_def_pecas is not None:
            self.on_open_def_pecas()

    def _open_materias_primas(self) -> None:
        """Open the raw materials page through the optional callback."""
        if self.on_open_materias_primas is not None:
            self.on_open_materias_primas()

    def _open_caminhos_sistema(self) -> None:
        """Open the system paths page through the optional callback."""
        if self.on_open_caminhos_sistema is not None:
            self.on_open_caminhos_sistema()

    def _open_operacoes_maquinas(self) -> None:
        """Open the operations / machines page through the optional callback."""
        if self.on_open_operacoes_maquinas is not None:
            self.on_open_operacoes_maquinas()

    def _show_future_message(self) -> None:
        """Show the placeholder message for future settings areas."""
        self.status_label.setText("Esta \u00e1rea ser\u00e1 desenvolvida numa fase posterior.")
