"""Pesquisa IA - fontes: Materias-Primas do V3 (local) + PHC (artigos ST)."""

from __future__ import annotations

import re
import unicodedata

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.services.phc_materiais_service import query_phc_materiais
from app.services.pesquisa_ia_search_service import PesquisaCatalogosService
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_quantity


class PesquisaIAPage(QWidget):
    TABLE_HEADERS = [
        "Fonte",
        "Ref",
        "Descri\u00e7\u00e3o",
        "Fam\u00edlia",
        "Fornecedor",
        "Pre\u00e7o Venda",
        "Pre\u00e7o Custo",
        "Unidade",
        "Stock",
        "Comp",
        "Larg",
        "Esp",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._v3: list[dict] = []
        self._phc: list[dict] = []
        self._resultados: list[dict] = []
        self._cat_service: PesquisaCatalogosService | None = None

        self.cabecalho = BarraCabecalho(
            "Pesquisa IA",
            ["Mat\u00e9rias-primas do V3 + PHC (Ferragens, Madeiras, Orlas)"],
        )

        self.carregar_button = QPushButton("Carregar/Atualizar (PHC)")
        self.carregar_button.clicked.connect(self.carregar_phc)
        self.catalogos_button = QPushButton("Pesquisar cat\u00e1logos (IA)")
        self.catalogos_button.clicked.connect(self.pesquisar_catalogos)
        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.carregar_button)
        actions_layout.addWidget(self.catalogos_button)
        actions_layout.addStretch()

        self.campo_pesquisa = CampoPesquisa(
            placeholder=(
                "Pesquisar refer\u00eancia, descri\u00e7\u00e3o, fornecedor\u2026 "
                "(espa\u00e7o p/ v\u00e1rios termos)"
            )
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self.aplicar_pesquisa)
        self.campo_pesquisa.limpar_clicado.connect(self.aplicar_pesquisa)

        self.status_label = QLabel("")

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
            self.table, "pesquisa_ia"
        )
        self._larguras_seed_feito = False

        self.catalogo_table = QTableWidget(0, 5)
        self.catalogo_table.setHorizontalHeaderLabels(
            ["Score", "Fornecedor", "Ficheiro", "Local", "Trecho"]
        )
        self.catalogo_table.verticalHeader().setVisible(False)
        self.catalogo_table.setAlternatingRowColors(True)
        self.catalogo_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.catalogo_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        ch = self.catalogo_table.horizontalHeader()
        ch.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        ch.setStretchLastSection(True)
        ch.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        self.catalogo_table.cellDoubleClicked.connect(self._abrir_catalogo)

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addWidget(self.campo_pesquisa)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=2)
        layout.addWidget(
            QLabel("Cat\u00e1logos (documentos) \u2014 duplo-clique abre o ficheiro:")
        )
        layout.addWidget(self.catalogo_table, stretch=1)
        self.setLayout(layout)

        self.carregar_v3()

    def carregar_v3(self) -> None:
        try:
            with SessionLocal() as session:
                materias = DefMateriaPrimaService(session).listar_materias_primas()
        except SQLAlchemyError:
            self._v3 = []
        else:
            self._v3 = [_do_v3(materia) for materia in materias]
        self._recombinar()

    def carregar_phc(self) -> None:
        self.status_label.setText("A carregar do PHC\u2026")
        self.carregar_button.setEnabled(False)
        try:
            with SessionLocal() as session:
                linhas = query_phc_materiais(session)
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"N\u00e3o foi poss\u00edvel ler o PHC: {exc}")
            self.carregar_button.setEnabled(True)
            return
        self._phc = [_do_phc(linha) for linha in linhas]
        self.carregar_button.setEnabled(True)
        self._recombinar()

    def _recombinar(self) -> None:
        self._resultados = self._v3 + self._phc
        self.aplicar_pesquisa()

    def aplicar_pesquisa(self, _text: str | None = None) -> None:
        texto = self.campo_pesquisa.texto()
        if not texto.strip():
            filtrados = self._resultados
        else:
            filtrados = [resultado for resultado in self._resultados if _corresponde(resultado, texto)]
        self._preencher_tabela(filtrados)

        total = len(self._resultados)
        sufixo = "" if self._phc else " \u2014 carregue o PHC para incluir o cat\u00e1logo PHC"
        if not total:
            self.status_label.setText("Sem dados.")
        elif texto.strip() and not filtrados:
            self.status_label.setText("Sem resultados para a pesquisa.")
        else:
            self.status_label.setText(
                f"{len(filtrados)} de {total} (V3: {len(self._v3)}, PHC: {len(self._phc)}){sufixo}"
            )

    def _preencher_tabela(self, linhas: list[dict]) -> None:
        self.table.setRowCount(len(linhas))
        for row_index, resultado in enumerate(linhas):
            valores = [
                resultado.get("Fonte", ""),
                resultado.get("Ref", ""),
                resultado.get("Descricao", ""),
                resultado.get("Familia", ""),
                resultado.get("Fornecedor", ""),
                format_currency(resultado.get("Preco_Venda")),
                format_currency(resultado.get("Preco_Custo")),
                resultado.get("Unidade", ""),
                format_quantity(resultado.get("Stock")),
                format_quantity(resultado.get("Comp")),
                format_quantity(resultado.get("Larg")),
                format_quantity(resultado.get("Esp")),
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                self.table.setItem(row_index, col, item)
        if not self._larguras_restauradas and not self._larguras_seed_feito and linhas:
            self.table.resizeColumnsToContents()
            self._larguras_seed_feito = True

    def _servico_catalogos(self) -> PesquisaCatalogosService:
        if self._cat_service is None:
            with SessionLocal() as session:
                self._cat_service = PesquisaCatalogosService(session)
        return self._cat_service

    def pesquisar_catalogos(self) -> None:
        texto = self.campo_pesquisa.texto().strip()
        if not texto:
            self.status_label.setText("Escreva algo para pesquisar nos cat\u00e1logos.")
            return
        servico = self._servico_catalogos()
        if not servico.disponivel():
            self.status_label.setText(
                "\u00cdndice de cat\u00e1logos n\u00e3o encontrado. Corra: "
                "python -m scripts.indexar_pesquisa_ia"
            )
            return
        self.status_label.setText("A pesquisar nos cat\u00e1logos (IA)\u2026")
        self.catalogos_button.setEnabled(False)
        try:
            resultados = servico.pesquisar(texto, top_n=30)
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"Erro na pesquisa de cat\u00e1logos: {exc}")
            self.catalogos_button.setEnabled(True)
            return
        self.catalogos_button.setEnabled(True)
        self._preencher_catalogos(resultados)
        self.status_label.setText(
            f"Cat\u00e1logos: {len(resultados)} resultados para \"{texto}\"."
        )

    def _preencher_catalogos(self, resultados) -> None:
        self.catalogo_table.setRowCount(len(resultados))
        for row_index, resultado in enumerate(resultados):
            valores = [
                f"{resultado.score:.3f}",
                resultado.fornecedor,
                resultado.ficheiro,
                resultado.local,
                resultado.trecho,
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, resultado.caminho)
                self.catalogo_table.setItem(row_index, col, item)

    def _abrir_catalogo(self, row: int, _col: int = 0) -> None:
        item = self.catalogo_table.item(row, 0)
        caminho = item.data(Qt.ItemDataRole.UserRole) if item is not None else None
        if caminho:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(caminho)))


def _do_phc(linha: dict) -> dict:
    return {
        "Fonte": "PHC",
        "Ref": str(linha.get("Ref") or "").strip(),
        "Descricao": str(linha.get("Descricao") or "").strip(),
        "Familia": str(linha.get("Familia_Nome") or linha.get("Familia") or "").strip(),
        "Fornecedor": str(linha.get("Fornecedor") or "").strip(),
        "Ref_Fornecedor": str(linha.get("Ref_Fornecedor") or "").strip(),
        "Preco_Venda": linha.get("Preco_Venda"),
        "Preco_Custo": linha.get("Preco_Custo"),
        "Unidade": str(linha.get("Unidade") or "").strip(),
        "Stock": linha.get("Stock"),
        "Comp": linha.get("Altura"),
        "Larg": linha.get("Largura"),
        "Esp": linha.get("Espessura"),
    }


def _do_v3(materia) -> dict:
    return {
        "Fonte": "V3",
        "Ref": (materia.ref_le or "").strip(),
        "Descricao": (materia.descricao or "").strip(),
        "Familia": (materia.familia_original_excel or "").strip(),
        "Fornecedor": (materia.fornecedor or "").strip(),
        "Ref_Fornecedor": "",
        "Preco_Venda": None,
        "Preco_Custo": materia.preco_liquido,
        "Unidade": (materia.unidade or "").strip(),
        "Stock": None,
        "Comp": materia.comprimento,
        "Larg": materia.largura,
        "Esp": materia.espessura,
    }


def _normalizar(value: object) -> str:
    if value is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(value))
    texto = "".join(caractere for caractere in texto if not unicodedata.combining(caractere))
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def _corresponde(resultado: dict, texto: str) -> bool:
    tokens = _normalizar(texto).split()
    if not tokens:
        return True
    alvo = _normalizar(
        " ".join(
            str(resultado.get(chave) or "")
            for chave in ("Ref", "Descricao", "Familia", "Fornecedor", "Ref_Fornecedor")
        )
    )
    return all(token in alvo for token in tokens)
