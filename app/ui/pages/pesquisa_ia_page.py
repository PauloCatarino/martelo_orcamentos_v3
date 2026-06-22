"""Pesquisa IA - 1a fatia: pesquisa nas materias-primas do PHC."""

from __future__ import annotations

import re
import unicodedata

from PySide6.QtGui import QColor
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

from app.db.session import SessionLocal
from app.services.phc_materiais_service import query_phc_materiais
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_quantity


class PesquisaIAPage(QWidget):
    TABLE_HEADERS = [
        "Ref",
        "Descri\u00e7\u00e3o",
        "Fam\u00edlia",
        "Fornecedor",
        "Pre\u00e7o Venda",
        "Pre\u00e7o Custo",
        "Unidade",
        "Stock",
        "Alt",
        "Larg",
        "Esp",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._linhas: list[dict] = []

        self.cabecalho = BarraCabecalho(
            "Pesquisa IA",
            ["Pesquisa nas mat\u00e9rias-primas do PHC (Ferragens, Madeiras, Orlas)"],
        )

        self.carregar_button = QPushButton("Carregar/Atualizar (PHC)")
        self.carregar_button.clicked.connect(self.carregar_phc)
        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.carregar_button)
        actions_layout.addStretch()

        self.campo_pesquisa = CampoPesquisa(
            placeholder=(
                "Pesquisar refer\u00eancia, descri\u00e7\u00e3o, fornecedor\u2026 "
                "(espa\u00e7o p/ v\u00e1rios termos)"
            )
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self.aplicar_pesquisa)
        self.campo_pesquisa.limpar_clicado.connect(self.aplicar_pesquisa)

        self.status_label = QLabel(
            "Clique em \u201cCarregar/Atualizar (PHC)\u201d para ler as "
            "mat\u00e9rias-primas do PHC."
        )

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
            self.table, "pesquisa_ia_phc"
        )
        self._larguras_seed_feito = False

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addWidget(self.campo_pesquisa)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=1)
        self.setLayout(layout)

    def carregar_phc(self) -> None:
        self.status_label.setText("A carregar do PHC\u2026")
        self.carregar_button.setEnabled(False)
        try:
            with SessionLocal() as session:
                self._linhas = query_phc_materiais(session)
        except Exception as exc:  # noqa: BLE001
            self._linhas = []
            self.status_label.setText(f"N\u00e3o foi poss\u00edvel ler o PHC: {exc}")
            self.carregar_button.setEnabled(True)
            return
        self.carregar_button.setEnabled(True)
        self.aplicar_pesquisa()

    def aplicar_pesquisa(self, _text: str | None = None) -> None:
        texto = self.campo_pesquisa.texto()
        if not texto.strip():
            filtrados = self._linhas
        else:
            filtrados = [linha for linha in self._linhas if _corresponde(linha, texto)]
        self._preencher_tabela(filtrados)
        if not self._linhas:
            self.status_label.setText("Sem dados (carregue do PHC).")
        elif texto.strip() and not filtrados:
            self.status_label.setText("Sem resultados para a pesquisa.")
        else:
            self.status_label.setText(f"{len(filtrados)} de {len(self._linhas)} artigos.")

    def _preencher_tabela(self, linhas: list[dict]) -> None:
        self.table.setRowCount(len(linhas))
        for row_index, linha in enumerate(linhas):
            valores = [
                str(linha.get("Ref") or "").strip(),
                str(linha.get("Descricao") or "").strip(),
                str(linha.get("Familia_Nome") or linha.get("Familia") or "").strip(),
                str(linha.get("Fornecedor") or "").strip(),
                format_currency(linha.get("Preco_Venda")),
                format_currency(linha.get("Preco_Custo")),
                str(linha.get("Unidade") or "").strip(),
                format_quantity(linha.get("Stock")),
                format_quantity(linha.get("Altura")),
                format_quantity(linha.get("Largura")),
                format_quantity(linha.get("Espessura")),
            ]
            for col, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                self.table.setItem(row_index, col, item)
        if not self._larguras_restauradas and not self._larguras_seed_feito and linhas:
            self.table.resizeColumnsToContents()
            self._larguras_seed_feito = True


def _normalizar(value: object) -> str:
    if value is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(value))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def _corresponde(linha: dict, texto: str) -> bool:
    tokens = _normalizar(texto).split()
    if not tokens:
        return True
    alvo = _normalizar(
        " ".join(
            str(linha.get(chave) or "")
            for chave in (
                "Ref",
                "Descricao",
                "Familia_Nome",
                "Fornecedor",
                "Ref_Fornecedor",
            )
        )
    )
    return all(token in alvo for token in tokens)
