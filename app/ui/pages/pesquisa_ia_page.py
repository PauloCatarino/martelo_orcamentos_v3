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
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.services.phc_materiais_service import query_phc_materiais
from app.services.placas_referencias_service import LinhaReferencia, listar_referencias
from app.services.pesquisa_ia_resposta_service import RespostaIAService
from app.services.pesquisa_ia_search_service import PesquisaCatalogosService
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras
from app.utils.formatters import format_currency, format_quantity

ESPESSURAS = [
    "8mm",
    "10mm",
    "12mm",
    "16mm",
    "18mm",
    "19mm",
    "22mm",
    "25mm",
    "30mm",
    "38mm",
]


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
        "Ref Fornec",
        "Data pre\u00e7o",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._v3: list[dict] = []
        self._phc: list[dict] = []
        self._resultados: list[dict] = []
        self._cat_service: PesquisaCatalogosService | None = None
        self._ultimos_catalogos: list = []
        self._filtrados_estrutural: list = []
        self._referencias_todas: list[LinhaReferencia] = []
        self._referencias_filtradas: list[LinhaReferencia] = []

        self.cabecalho = BarraCabecalho(
            "Pesquisa IA",
            ["Mat\u00e9rias-primas do V3 + PHC (Ferragens, Madeiras, Orlas)"],
        )

        self.carregar_button = QPushButton("Carregar/Atualizar (PHC)")
        self.carregar_button.clicked.connect(self.carregar_phc)
        self.catalogos_button = QPushButton("Pesquisar cat\u00e1logos (IA)")
        self.catalogos_button.clicked.connect(self.pesquisar_catalogos)
        self.referencias_button = QPushButton("Carregar refer\u00eancias (placas)")
        self.referencias_button.clicked.connect(self.carregar_referencias)
        self.resposta_button = QPushButton("Gerar resposta IA")
        self.resposta_button.clicked.connect(self.gerar_resposta)
        actions_layout = QHBoxLayout()
        actions_layout.addWidget(self.carregar_button)
        actions_layout.addWidget(self.catalogos_button)
        actions_layout.addWidget(self.referencias_button)
        actions_layout.addWidget(self.resposta_button)
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
        ligar_persistencia_larguras(self.catalogo_table, "pesquisa_ia_catalogos")
        self.catalogo_table.cellDoubleClicked.connect(self._abrir_catalogo)

        cols_ref = [
            "Folha",
            "Refer\u00eancia",
            "ST/Acab",
            "Nome Design",
            "Grupo",
            "Tipo Produto",
            "Fornecedor",
            *ESPESSURAS,
        ]
        self.referencias_table = QTableWidget(0, len(cols_ref))
        self.referencias_table.setHorizontalHeaderLabels(cols_ref)
        self.referencias_table.verticalHeader().setVisible(False)
        self.referencias_table.setAlternatingRowColors(True)
        self.referencias_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.referencias_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        rh = self.referencias_table.horizontalHeader()
        rh.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        rh.setStretchLastSection(True)
        rh.setStyleSheet(
            f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
            f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
        )
        ligar_persistencia_larguras(self.referencias_table, "pesquisa_ia_referencias")

        self.resposta_text = QTextEdit()
        self.resposta_text.setReadOnly(True)
        self.resposta_text.setMinimumHeight(120)
        self.resposta_text.setPlaceholderText(
            "A resposta IA (com cita\u00e7\u00f5es) aparece aqui depois de "
            "'Pesquisar cat\u00e1logos (IA)' + 'Gerar resposta IA'."
        )

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(actions_layout)
        layout.addWidget(self.campo_pesquisa)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, stretch=2)
        layout.addWidget(QLabel("Refer\u00eancias de placas (cat\u00e1logo curado):"))
        layout.addWidget(self.referencias_table, stretch=2)
        layout.addWidget(
            QLabel("Cat\u00e1logos (documentos) \u2014 duplo-clique abre o ficheiro:")
        )
        layout.addWidget(self.catalogo_table, stretch=1)
        layout.addWidget(QLabel("Resposta IA (com cita\u00e7\u00f5es):"))
        layout.addWidget(self.resposta_text, stretch=1)
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

    def carregar_referencias(self) -> None:
        self.status_label.setText("A carregar refer\u00eancias de placas\u2026")
        self.referencias_button.setEnabled(False)
        try:
            with SessionLocal() as session:
                self._referencias_todas = listar_referencias(session)
        except Exception as exc:  # noqa: BLE001
            self.referencias_button.setEnabled(True)
            self.status_label.setText(
                f"N\u00e3o foi poss\u00edvel ler o Excel de refer\u00eancias: {exc}"
            )
            return

        self.referencias_button.setEnabled(True)
        self.aplicar_pesquisa()

    def _recombinar(self) -> None:
        self._resultados = self._v3 + self._phc
        self.aplicar_pesquisa()

    def aplicar_pesquisa(self, _text: str | None = None) -> None:
        texto = self.campo_pesquisa.texto()
        if not texto.strip():
            filtrados = self._resultados
        else:
            filtrados = [resultado for resultado in self._resultados if _corresponde(resultado, texto)]
        self._filtrados_estrutural = filtrados
        self._preencher_tabela(filtrados)
        if not texto.strip():
            referencias = self._referencias_todas
        else:
            referencias = [
                referencia
                for referencia in self._referencias_todas
                if _ref_corresponde(referencia, texto)
            ]
        self._referencias_filtradas = referencias
        self._preencher_referencias(referencias)

        total = len(self._resultados)
        total_referencias = len(self._referencias_todas)
        sufixo = "" if self._phc else " \u2014 carregue o PHC para incluir o cat\u00e1logo PHC"
        sufixo_referencias = (
            f"; refer\u00eancias: {len(referencias)} de {total_referencias}"
            if total_referencias
            else ""
        )
        if not total and not total_referencias:
            self.status_label.setText("Sem dados.")
        elif texto.strip() and not filtrados and not referencias:
            self.status_label.setText("Sem resultados para a pesquisa.")
        elif not total:
            self.status_label.setText(
                f"Refer\u00eancias: {len(referencias)} de {total_referencias}."
            )
        else:
            self.status_label.setText(
                f"{len(filtrados)} de {total} "
                f"(V3: {len(self._v3)}, PHC: {len(self._phc)})"
                f"{sufixo}{sufixo_referencias}"
            )

    def _preencher_referencias(self, referencias: list[LinhaReferencia]) -> None:
        self.referencias_table.setRowCount(len(referencias))
        for row_index, referencia in enumerate(referencias):
            base = [
                referencia.folha,
                referencia.referencia,
                referencia.st_acab,
                referencia.nome_design,
                referencia.grupo,
                referencia.tipo,
                referencia.fornecedor,
            ]
            precos = [
                referencia.precos.get(espessura, "") for espessura in ESPESSURAS
            ]
            for col, valor in enumerate(base + precos):
                item = QTableWidgetItem(valor)
                item.setBackground(QColor(tema.cor_zebra(row_index)))
                self.referencias_table.setItem(row_index, col, item)

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
                str(resultado.get("Ref_Fornecedor") or ""),
                str(resultado.get("Data_Preco") or ""),
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
        self._ultimos_catalogos = resultados
        self._preencher_catalogos(resultados)
        self.status_label.setText(
            f"Cat\u00e1logos: {len(resultados)} resultados para \"{texto}\"."
        )

    def gerar_resposta(self) -> None:
        pergunta = self.campo_pesquisa.texto().strip()
        if not pergunta:
            self.status_label.setText("Escreva uma pergunta no campo de pesquisa.")
            return
        artigos = self._filtrados_estrutural[:15]
        trechos = self._ultimos_catalogos[:8]
        if not artigos and not trechos and not self._referencias_filtradas:
            self.status_label.setText(
                "Sem dados \u2014 pesquise primeiro (e carregue o PHC / cat\u00e1logos)."
            )
            return

        partes: list[str] = []
        if artigos:
            linhas = [
                f"- [{resultado.get('Fonte')}] {resultado.get('Ref')}: "
                f"{resultado.get('Descricao')} "
                f"| {resultado.get('Familia')} | {resultado.get('Fornecedor')} "
                f"| custo {format_currency(resultado.get('Preco_Custo'))} "
                f"| {format_quantity(resultado.get('Comp'))}x"
                f"{format_quantity(resultado.get('Larg'))}x"
                f"{format_quantity(resultado.get('Esp'))}"
                for resultado in artigos
            ]
            partes.append(
                "ARTIGOS (mat\u00e9rias-primas PHC/V3):\n" + "\n".join(linhas)
            )
        refs = self._referencias_filtradas[:10]
        if refs:
            linhas = []
            for referencia in refs:
                precos = (
                    "; ".join(
                        f"{espessura} {preco}"
                        for espessura, preco in referencia.precos.items()
                    )
                    or "(sem pre\u00e7os)"
                )
                linhas.append(
                    f"- Ref {referencia.referencia} "
                    f"({referencia.fornecedor or referencia.folha}) | "
                    f"{referencia.st_acab} | {referencia.nome_design} | "
                    f"Grupo {referencia.grupo} | {referencia.tipo} | "
                    f"Pre\u00e7os por espessura: {precos}"
                )
            partes.append(
                "REFER\u00caNCIAS DE PLACAS (cat\u00e1logo curado):\n"
                + "\n".join(linhas)
            )
        if trechos:
            linhas = [
                f"[{i}] ({resultado.ficheiro} \u00b7 {resultado.local}) "
                f"{resultado.trecho}"
                for i, resultado in enumerate(trechos, start=1)
            ]
            partes.append("TRECHOS DE CAT\u00c1LOGOS:\n" + "\n".join(linhas))
        contexto = "\n\n".join(partes)

        self.status_label.setText("A gerar resposta IA\u2026")
        self.resposta_button.setEnabled(False)
        try:
            with SessionLocal() as session:
                resposta = RespostaIAService(session).gerar(pergunta, contexto)
        except Exception as exc:  # noqa: BLE001
            self.resposta_button.setEnabled(True)
            self.status_label.setText(f"Erro a gerar resposta: {exc}")
            return
        self.resposta_button.setEnabled(True)
        self.resposta_text.setPlainText(resposta or "(sem resposta)")
        self.status_label.setText("Resposta gerada.")

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
        "Data_Preco": str(linha.get("Data_Preco") or "").strip(),
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
        "Ref_Fornecedor": (
            getattr(materia, "referencia_fornecedor", "") or ""
        ).strip(),
        "Data_Preco": "",
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


def _ref_corresponde(referencia: LinhaReferencia, texto: str) -> bool:
    tokens = _normalizar(texto).split()
    if not tokens:
        return True
    alvo = _normalizar(
        " ".join(
            [
                referencia.referencia,
                referencia.st_acab,
                referencia.nome_design,
                referencia.grupo,
                referencia.fornecedor,
                referencia.tipo,
            ]
        )
    )
    return all(token in alvo for token in tokens)
