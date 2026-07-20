"""Raw materials catalog page."""

from __future__ import annotations

import re
import unicodedata

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
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
from app.domain.numeros import formatar_percentagem, normalize_percentagem_humana
from app.repositories.def_materia_prima_repository import DefMateriaPrimaResumo
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.colunas_visiveis import ligar_menu_colunas
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_quantity


class MateriasPrimasPage(QWidget):
    """Page for listing imported raw materials."""

    TABLE_HEADERS = [
        "Ref LE",
        "Descri\u00e7\u00e3o",
        "Tipo Excel",
        "Fam\u00edlia Excel",
        "Unidade",
        "Desp %",
        "Pre\u00e7o L\u00edquido",
        "Orla 0.4",
        "Orla 1.0",
        "Comp MP",
        "Larg MP",
        "Esp MP",
        "Ativo",
    ]

    def __init__(self) -> None:
        super().__init__()

        self._materias_primas: list[DefMateriaPrimaResumo] = []

        self.cabecalho = BarraCabecalho(
            "Mat\u00e9rias-Primas",
            [
                "Cat\u00e1logo de mat\u00e9rias-primas importado a partir do Excel. "
                "Estes dados ser\u00e3o usados futuramente nas configura\u00e7\u00f5es de "
                "or\u00e7amento, items e custeio."
            ],
        )

        self.refresh_button = QPushButton("Atualizar Página")
        self.refresh_button.clicked.connect(self.carregar_materias_primas)
        self.refresh_button.setToolTip("Recarregar as matérias-primas importadas")

        self.import_button = QPushButton("Importar/Atualizar Excel")
        self.import_button.clicked.connect(self.importar_do_excel)
        self.import_button.setToolTip(
            "Importar ou atualizar o catálogo a partir do Excel configurado"
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("materiasPrimasStatus")

        self.campo_pesquisa = CampoPesquisa(
            placeholder="Pesquisar mat\u00e9ria-prima\u2026 (espa\u00e7o para v\u00e1rios termos)"
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self.aplicar_pesquisa)
        self.campo_pesquisa.limpar_clicado.connect(self.aplicar_pesquisa)

        self.open_excel_button = QPushButton("Abrir Excel")
        self.open_excel_button.setToolTip(
            "Abrir o ficheiro Excel de origem das matérias-primas"
        )
        self.open_excel_button.clicked.connect(self.abrir_excel)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.campo_pesquisa)
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.open_excel_button)
        toolbar.addWidget(self.refresh_button)
        toolbar.addStretch()

        self.table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(False)
        header.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        self._larguras_restauradas = ligar_persistencia_larguras(
            self.table, "materias_primas"
        )
        ligar_menu_colunas(self.table, "materias_primas")
        self._larguras_seed_feito = False
        # Mapa linha->matéria-prima e "modo resolução" (assistente): duplo-clique
        # aplica a matéria-prima à linha do custeio e volta.
        self._materias_por_row: dict[int, DefMateriaPrimaResumo] = {}
        self._resolucao_callback = None
        self.table.cellDoubleClicked.connect(self._on_duplo_clique)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(toolbar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)

        self.setLayout(layout)
        self.carregar_materias_primas()

    def abrir_excel(self) -> None:
        """Open the configured source workbook without modifying it."""
        from scripts.import_materias_primas_excel import (
            get_default_excel_path_resolution,
            resolve_excel_path,
        )

        try:
            with SessionLocal() as session:
                resolucao = resolve_excel_path(session=session)
                esperada = get_default_excel_path_resolution(session).path
        except (SQLAlchemyError, OSError):
            self.status_label.setText("Não foi possível localizar o Excel configurado.")
            return

        if resolucao is None:
            self.status_label.setText(f"Ficheiro Excel não encontrado: {esperada}")
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(resolucao.path)))

    def carregar_materias_primas(self) -> None:
        """Load raw materials into the table."""
        self.table.setRowCount(0)
        self.status_label.clear()
        self._materias_primas = []

        try:
            with SessionLocal() as session:
                materias_primas = DefMateriaPrimaService(session).listar_materias_primas()
        except SQLAlchemyError:
            self.status_label.setText("Nao foi possivel carregar as materias-primas.")
            return

        self._materias_primas = materias_primas
        self.aplicar_pesquisa()

        if not materias_primas:
            self.status_label.setText("Sem materias-primas para mostrar.")

    def importar_do_excel(self) -> None:
        """Run the real raw-material import from the configured Excel (upsert by ref_le)."""
        confirm = QMessageBox.question(
            self,
            "Importar/Atualizar Excel",
            "Esta operação vai atualizar as matérias-primas a partir do Excel "
            "configurado. As referências existentes serão atualizadas e não "
            "duplicadas. Deseja continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            from scripts.import_materias_primas_excel import importar_materias_primas

            with SessionLocal() as session:
                summary = importar_materias_primas(session)
        except FileNotFoundError as error:
            print(f"[Materias-Primas] Excel nao encontrado: {error}")
            self.status_label.setText(
                "Ficheiro Excel de matérias-primas não encontrado. "
                "Verifique a configuração."
            )
            return
        except (ImportError, SQLAlchemyError, RuntimeError, OSError) as error:
            print(f"[Materias-Primas] Erro ao importar do Excel: {error}")
            self.status_label.setText(
                "Não foi possível importar as matérias-primas do Excel."
            )
            return

        self.carregar_materias_primas()
        self.status_label.setText(
            f"Importação concluída: {summary.criadas} criadas, "
            f"{summary.atualizadas} atualizadas, {summary.erros} erros."
        )

    def aplicar_pesquisa(self, _text: str | None = None) -> None:
        """Filter the loaded raw materials according to the search text."""
        self.status_label.clear()
        search_text = self.campo_pesquisa.texto()

        if not search_text.strip():
            filtered = self._materias_primas
        else:
            filtered = [
                materia
                for materia in self._materias_primas
                if materia_matches_search(materia, search_text)
            ]

        self._preencher_tabela(filtered)

        if not self._materias_primas:
            self.status_label.setText("Sem materias-primas para mostrar.")
        elif search_text.strip() and not filtered:
            self.status_label.setText("Sem resultados para a pesquisa.")

    def focar_materia_prima(self, ref_le: str | None) -> None:
        """Filtra pela Ref LE, seleciona e pisca a matéria-prima (assistente 3B)."""
        if not ref_le:
            return
        alvo = ref_le.strip().upper()
        # Filtrar pela Ref LE isola a matéria-prima na tabela (re-preenche já).
        self.campo_pesquisa.definir_texto(ref_le)
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item is not None and (item.text() or "").strip().upper() == alvo:
                self.table.selectRow(row)
                self.table.scrollToItem(
                    item, QAbstractItemView.ScrollHint.PositionAtCenter
                )
                self._piscar_linha(row)
                return

    def _piscar_linha(self, row: int) -> None:
        """Pisca a linha (fundo ocre) durante ~1,5 s e repõe o fundo original."""
        itens = [
            self.table.item(row, col) for col in range(self.table.columnCount())
        ]
        itens = [item for item in itens if item is not None]
        fundos = [item.background() for item in itens]
        realce = QColor(tema.OCRE_SUAVE)
        for item in itens:
            item.setBackground(realce)

        def repor() -> None:
            for item, fundo in zip(itens, fundos):
                item.setBackground(fundo)

        QTimer.singleShot(1500, repor)

    def entrar_modo_resolucao(self, ao_escolher) -> None:
        """Ativa o modo resolução: duplo-clique aplica a matéria-prima (assistente 3B)."""
        self._resolucao_callback = ao_escolher
        self.status_label.setText(
            "A resolver: duplo-clique numa matéria-prima para a aplicar à linha e voltar."
        )

    def sair_modo_resolucao(self) -> None:
        self._resolucao_callback = None

    def _on_duplo_clique(self, row: int, _column: int) -> None:
        callback = self._resolucao_callback
        materia = self._materias_por_row.get(row)
        if callback is not None and materia is not None:
            self.sair_modo_resolucao()
            callback(materia)

    def _preencher_tabela(self, materias_primas: list[DefMateriaPrimaResumo]) -> None:
        """Fill the table with raw material read models."""
        self.table.setRowCount(len(materias_primas))
        self._materias_por_row = {}

        for row_index, materia in enumerate(materias_primas):
            self._materias_por_row[row_index] = materia
            values = [
                materia.ref_le or "",
                materia.descricao,
                materia.tipo_original_excel or "",
                materia.familia_original_excel or "",
                materia.unidade or "",
                formatar_percentagem(
                    normalize_percentagem_humana(materia.desperdicio_percentagem)
                ),
                format_currency(materia.preco_liquido),
                materia.coresp_orla_0_4 or "",
                materia.coresp_orla_1_0 or "",
                format_quantity(materia.comprimento),
                format_quantity(materia.largura),
                format_quantity(materia.espessura),
                "Sim" if materia.ativo else "N\u00e3o",
            ]

            for column_index, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                self.table.setItem(row_index, column_index, item)

        if (
            not self._larguras_restauradas
            and not self._larguras_seed_feito
            and materias_primas
        ):
            self.table.resizeColumnsToContents()
            self._larguras_seed_feito = True


def normalize_search_text(value: object) -> str:
    """Normalize text for accent-insensitive, case-insensitive search."""
    if value is None:
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def materia_matches_search(materia: DefMateriaPrimaResumo, search_text: str) -> bool:
    """Return whether a raw material matches all search tokens."""
    tokens = normalize_search_text(search_text).split()
    if not tokens:
        return True

    searchable_text = normalize_search_text(
        " ".join(
            [
                materia.ref_le or "",
                materia.descricao,
                materia.tipo_original_excel or "",
                materia.familia_original_excel or "",
                materia.unidade or "",
                materia.fornecedor or "",
            ]
        )
    )

    return all(token in searchable_text for token in tokens)
