"""System paths/settings page."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
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
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.repositories.system_setting_repository import SystemSettingResumo
from app.services.system_setting_service import SystemSettingService
from app.domain.pesquisa_texto import corresponde_texto, normalizar
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


def configuracao_corresponde(configuracao, procurado: str) -> bool:
    """Se este caminho deve aparecer para o que está escrito na pesquisa.

    Procura no nome da chave, na descrição, no grupo e no próprio valor — quem
    anda à procura tanto se lembra do nome ("instaladores") como do sítio
    ("SERVER_LE"). Aceita palavras soltas (sem acentos, singular ou plural) e
    também um pedaço de palavra, porque quem procura escreve "instala" e não
    espera ter de acertar na palavra inteira.
    """
    texto = (procurado or "").strip()
    if not texto:
        return True

    campos = [
        configuracao.chave or "",
        configuracao.descricao or "",
        configuracao.grupo or "",
        configuracao.valor or "",
    ]
    if corresponde_texto(campos, texto):
        return True

    return normalizar(texto) in normalizar(" ".join(campos))


class CaminhosSistemaPage(QWidget):
    """Page for editing system paths and related technical settings."""

    TABLE_HEADERS = [
        "Descri\u00e7\u00e3o / Campo",
        "Valor",
        "Procurar",
    ]
    BROWSE_TYPES = {"pasta", "ficheiro"}

    def __init__(self, on_back=None) -> None:
        super().__init__()

        self.on_back = on_back
        self._settings_by_row: dict[int, SystemSettingResumo] = {}
        #: Tudo o que veio da base; a tabela mostra só o que passa a pesquisa.
        self._configuracoes: list[SystemSettingResumo] = []

        self.cabecalho = BarraCabecalho(
            "Caminhos do Sistema",
            [
                "Configura\u00e7\u00e3o dos caminhos usados pelo Martelo V3 para ficheiros "
                "externos, produ\u00e7\u00e3o, mat\u00e9rias-primas, CNC, IMOS e IA."
            ],
        )

        self.save_button = QPushButton("Guardar Configura\u00e7\u00f5es")
        self.save_button.clicked.connect(self.guardar_configuracoes)

        self.refresh_button = QPushButton("Atualizar")
        self.refresh_button.clicked.connect(self.carregar_configuracoes)

        self.voltar_button = QPushButton("Voltar às Configurações")
        self.voltar_button.setToolTip("Regressar ao menu Configurações.")
        self.voltar_button.clicked.connect(
            lambda: self.on_back() if self.on_back else None
        )

        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.save_button)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addStretch()
        actions_layout.addWidget(self.voltar_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("caminhosSistemaStatus")

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        ligar_persistencia_larguras(self.table, "caminhos_sistema")

        # São mais de meia centena de linhas: sem pesquisa, encontrar um
        # caminho pelo nome era percorrer a lista toda com os olhos.
        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar caminho — nome, descrição ou valor…"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self.aplicar_pesquisa)
        self.campo_pesquisa.limpar_clicado.connect(self.aplicar_pesquisa)

        pesquisa_layout = QHBoxLayout()
        pesquisa_layout.addWidget(self.campo_pesquisa)
        pesquisa_layout.addStretch()

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(pesquisa_layout)
        layout.addLayout(actions_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_configuracoes()

    def carregar_configuracoes(self) -> None:
        """Load system settings into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()
        self._settings_by_row = {}

        try:
            with SessionLocal() as session:
                configuracoes = SystemSettingService(session).listar_configuracoes()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar os caminhos do sistema.")
            return

        self._configuracoes = configuracoes
        self.aplicar_pesquisa()

    def aplicar_pesquisa(self, _texto: str | None = None) -> None:
        """Mostrar só os caminhos que correspondem ao que está escrito."""
        procurado = self.campo_pesquisa.texto()
        visiveis = [
            configuracao
            for configuracao in self._configuracoes
            if configuracao_corresponde(configuracao, procurado)
        ]

        self._preencher_tabela(visiveis)

        if not self._configuracoes:
            self.status_label.setText("Sem caminhos do sistema para mostrar.")
        elif not visiveis:
            self.status_label.setText(
                f"Sem resultados para «{procurado}». Limpe a pesquisa (pincel) "
                "para ver os caminhos todos."
            )
        elif procurado.strip():
            self.status_label.setText(
                f"{len(visiveis)} de {len(self._configuracoes)} caminhos à vista."
            )
        else:
            self.status_label.setText(
                f"{len(self._configuracoes)} caminhos do sistema."
            )

    def guardar_configuracoes(self) -> None:
        """Save edited setting values."""
        valores: dict[str, str | None] = {}

        for row_index, setting in self._settings_by_row.items():
            value_item = self.table.item(row_index, 1)
            valores[setting.chave] = value_item.text() if value_item is not None else ""

        try:
            with SessionLocal() as session:
                SystemSettingService(session).guardar_varios(valores)
        except (SQLAlchemyError, ValueError):
            self.status_label.setText("Nao foi possivel guardar os caminhos do sistema.")
            return

        self.status_label.setText("Configuracoes guardadas com sucesso.")
        QMessageBox.information(
            self,
            "Caminhos do Sistema",
            "Configuracoes guardadas com sucesso.",
        )
        self.carregar_configuracoes()

    def _preencher_tabela(self, configuracoes: list[SystemSettingResumo]) -> None:
        """Fill the table with system setting read models."""
        self._settings_by_row = {}
        self.table.setRowCount(len(configuracoes))

        for row_index, setting in enumerate(configuracoes):
            self._settings_by_row[row_index] = setting
            dica = setting.descricao or setting.chave

            label_item = QTableWidgetItem(setting.descricao or setting.chave)
            label_item.setData(Qt.ItemDataRole.UserRole, setting.chave)
            label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            label_item.setToolTip(dica)

            value_item = QTableWidgetItem(setting.valor or "")
            value_item.setToolTip(dica)

            self.table.setItem(row_index, 0, label_item)
            self.table.setItem(row_index, 1, value_item)

            browse_button = QPushButton("Procurar...")
            browse_button.setEnabled(setting.tipo in self.BROWSE_TYPES)
            browse_button.setToolTip(f"Selecionar: {dica}")
            browse_button.clicked.connect(lambda _checked=False, row=row_index: self._procurar(row))
            self.table.setCellWidget(row_index, 2, browse_button)

    def _procurar(self, row_index: int) -> None:
        """Open a basic file/folder chooser for the selected row."""
        setting = self._settings_by_row.get(row_index)
        if setting is None:
            return

        current_item = self.table.item(row_index, 1)
        current_value = current_item.text() if current_item is not None else ""

        if setting.tipo == "pasta":
            selected = QFileDialog.getExistingDirectory(
                self,
                "Selecionar pasta",
                current_value,
            )
        elif setting.tipo == "ficheiro":
            selected, _ = QFileDialog.getOpenFileName(
                self,
                "Selecionar ficheiro",
                current_value,
            )
        else:
            selected = ""

        if selected:
            self.table.setItem(row_index, 1, QTableWidgetItem(selected))
