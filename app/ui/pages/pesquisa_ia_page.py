"""Pesquisa IA - fontes: Materias-Primas do V3 (local) + PHC (artigos ST)."""

from __future__ import annotations

import re
import unicodedata

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QTextCursor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.numeros import formatar_percentagem, normalize_percentagem_humana
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.services.phc_materiais_service import query_phc_materiais
from app.services.placas_referencias_service import LinhaReferencia, listar_referencias
from app.services.pesquisa_ia_resposta_service import RespostaIAService
from app.services.pesquisa_ia_search_service import PesquisaCatalogosService
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa
from app.ui.widgets.estado_splitter import ligar_persistencia_splitter
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


def _nova_tabela(
    headers: list[str], chave: str, *, esticar_ultima: bool = False
) -> tuple[QTableWidget, bool]:
    tabela = QTableWidget(0, len(headers))
    tabela.setHorizontalHeaderLabels(headers)
    tabela.verticalHeader().setVisible(False)
    tabela.setAlternatingRowColors(True)
    tabela.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    tabela.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    cabecalho = tabela.horizontalHeader()
    cabecalho.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    cabecalho.setStretchLastSection(esticar_ultima)
    cabecalho.setStyleSheet(
        f"QHeaderView::section {{ background-color: {tema.BEGE_AREIA}; "
        f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 3px; }}"
    )
    restaurado = ligar_persistencia_larguras(tabela, chave)
    return tabela, restaurado


def _seccao(titulo: str, widget: QWidget) -> QWidget:
    """Agrupa um rotulo + widget numa caixa, para ser um painel do splitter."""
    caixa = QWidget()
    vbox = QVBoxLayout(caixa)
    vbox.setContentsMargins(0, 0, 0, 0)
    vbox.setSpacing(4)
    vbox.addWidget(QLabel(titulo))
    vbox.addWidget(widget)
    return caixa


class _RespostaWorker(QObject):
    """Gera a resposta IA fora da thread da UI, emitindo pedacos (streaming)."""

    pedaco = Signal(str)
    falhou = Signal(str)
    concluido = Signal()

    def __init__(self, pergunta: str, contexto: str) -> None:
        super().__init__()
        self._pergunta = pergunta
        self._contexto = contexto

    def run(self) -> None:
        try:
            with SessionLocal() as session:
                servico = RespostaIAService(session)
                for pedaco in servico.gerar_stream(self._pergunta, self._contexto):
                    self.pedaco.emit(pedaco)
        except Exception as exc:  # noqa: BLE001
            self.falhou.emit(str(exc))
            return
        self.concluido.emit()


class PesquisaIAPage(QWidget):
    V3_HEADERS = [
        "Ref LE",
        "Ref Forn",
        "Descri\u00e7\u00e3o",
        "Pre\u00e7o tab",
        "Mrg (+)",
        "Desc (-)",
        "P. L\u00edq",
        "Und",
        "Orla 0.4",
        "Orla 1.0",
        "Comp",
        "Larg",
        "Esp",
        "Fabricante",
        "Atualizado",
    ]
    PHC_HEADERS = [
        "Ref",
        "Ref Forn",
        "Descri\u00e7\u00e3o",
        "Fam\u00edlia",
        "Fornecedor",
        "Pre\u00e7o Custo",
        "\u00dalt. Venda",
        "Und",
        "Stock",
        "Comp",
        "Larg",
        "Esp",
        "Data pre\u00e7o",
        "Obs",
    ]

    def __init__(self) -> None:
        super().__init__()
        self._v3: list = []
        self._phc: list[dict] = []
        self._v3_filtrados: list = []
        self._phc_filtrados: list[dict] = []
        self._cat_service: PesquisaCatalogosService | None = None
        self._ultimos_catalogos: list = []
        self._referencias_todas: list[LinhaReferencia] = []
        self._referencias_filtradas: list[LinhaReferencia] = []
        self._resposta_thread: QThread | None = None
        self._resposta_worker: _RespostaWorker | None = None

        self.cabecalho = BarraCabecalho(
            "Pesquisa IA",
            ["Mat\u00e9rias-primas do V3 + PHC (Ferragens, Madeiras, Orlas)"],
        )

        self.carregar_button = QPushButton("Carregar/Atualizar (PHC)")
        self.carregar_button.clicked.connect(self.carregar_phc)
        self.carregar_button.setToolTip("Carregar ou atualizar artigos do PHC")
        self.catalogos_button = QPushButton("Pesquisar cat\u00e1logos (IA)")
        self.catalogos_button.clicked.connect(self.pesquisar_catalogos)
        self.catalogos_button.setToolTip("Pesquisar catálogos externos com IA")
        self.referencias_button = QPushButton("Carregar refer\u00eancias (placas)")
        self.referencias_button.clicked.connect(self.carregar_referencias)
        self.referencias_button.setToolTip("Carregar referências de placas do Excel")
        self.resposta_button = QPushButton("Gerar resposta IA")
        self.resposta_button.clicked.connect(self.gerar_resposta)
        self.resposta_button.setToolTip("Gerar uma resposta IA a partir dos resultados")
        self.campo_pesquisa = CampoPesquisa(
            placeholder=(
                "Pesquisar refer\u00eancia, descri\u00e7\u00e3o, fornecedor... "
                "(espa\u00e7o p/ v\u00e1rios termos)"
            )
        )
        self.campo_pesquisa.pesquisa_mudou.connect(self.aplicar_pesquisa)
        self.campo_pesquisa.limpar_clicado.connect(self.aplicar_pesquisa)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.campo_pesquisa)
        toolbar.addWidget(self.carregar_button)
        toolbar.addWidget(self.catalogos_button)
        toolbar.addWidget(self.referencias_button)
        toolbar.addWidget(self.resposta_button)
        toolbar.addStretch()

        self.status_label = QLabel("")

        self.v3_table, self._v3_restaurado = _nova_tabela(
            self.V3_HEADERS, "pesquisa_ia_v3"
        )
        self._v3_seed = False
        self.phc_table, self._phc_restaurado = _nova_tabela(
            self.PHC_HEADERS, "pesquisa_ia_phc"
        )
        self._phc_seed = False

        self.catalogo_table, _ = _nova_tabela(
            ["Score", "Fornecedor", "Ficheiro", "Local", "Trecho"],
            "pesquisa_ia_catalogos",
            esticar_ultima=True,
        )
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
        self.referencias_table, _ = _nova_tabela(
            cols_ref, "pesquisa_ia_referencias", esticar_ultima=True
        )

        self.resposta_text = QTextEdit()
        self.resposta_text.setReadOnly(True)
        self.resposta_text.setMinimumHeight(120)
        self.resposta_text.setPlaceholderText(
            "A resposta IA (com cita\u00e7\u00f5es) aparece aqui depois de "
            "'Pesquisar cat\u00e1logos (IA)' + 'Gerar resposta IA'."
        )

        self.tabelas_splitter = QSplitter(Qt.Orientation.Vertical)
        self.tabelas_splitter.setChildrenCollapsible(False)
        self.tabelas_splitter.addWidget(
            _seccao("Mat\u00e9rias-primas V3 (interno):", self.v3_table)
        )
        self.tabelas_splitter.addWidget(
            _seccao("Artigos PHC (Ferragens, Madeiras, Orlas):", self.phc_table)
        )
        self.tabelas_splitter.addWidget(
            _seccao(
                "Refer\u00eancias de placas (cat\u00e1logo curado):",
                self.referencias_table,
            )
        )
        self.tabelas_splitter.addWidget(
            _seccao(
                "Cat\u00e1logos (documentos) - duplo-clique abre o ficheiro:",
                self.catalogo_table,
            )
        )
        self.tabelas_splitter.addWidget(
            _seccao("Resposta IA (com cita\u00e7\u00f5es):", self.resposta_text)
        )
        for indice, fator in enumerate((2, 2, 2, 1, 1)):
            self.tabelas_splitter.setStretchFactor(indice, fator)
        ligar_persistencia_splitter(self.tabelas_splitter, "pesquisa_ia")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(self.cabecalho)
        layout.addLayout(toolbar)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabelas_splitter, stretch=1)
        self.setLayout(layout)

        self.carregar_v3()

    def carregar_v3(self) -> None:
        try:
            with SessionLocal() as session:
                self._v3 = DefMateriaPrimaService(session).listar_materias_primas()
        except SQLAlchemyError:
            self._v3 = []
        self.aplicar_pesquisa()

    def carregar_phc(self) -> None:
        self.status_label.setText("A carregar do PHC...")
        self.carregar_button.setEnabled(False)
        try:
            with SessionLocal() as session:
                self._phc = query_phc_materiais(session)
        except Exception as exc:  # noqa: BLE001
            self.status_label.setText(f"N\u00e3o foi poss\u00edvel ler o PHC: {exc}")
            self.carregar_button.setEnabled(True)
            return
        self.carregar_button.setEnabled(True)
        self.aplicar_pesquisa()

    def carregar_referencias(self) -> None:
        self.status_label.setText("A carregar refer\u00eancias de placas...")
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

    def aplicar_pesquisa(self, _text: str | None = None) -> None:
        texto = self.campo_pesquisa.texto()
        if texto.strip():
            self._v3_filtrados = [
                materia for materia in self._v3 if _v3_corresponde(materia, texto)
            ]
            self._phc_filtrados = [
                linha for linha in self._phc if _phc_corresponde(linha, texto)
            ]
            self._referencias_filtradas = [
                referencia
                for referencia in self._referencias_todas
                if _ref_corresponde(referencia, texto)
            ]
        else:
            self._v3_filtrados = self._v3
            self._phc_filtrados = self._phc
            self._referencias_filtradas = self._referencias_todas

        self._preencher_v3(self._v3_filtrados)
        self._preencher_phc(self._phc_filtrados)
        self._preencher_referencias(self._referencias_filtradas)
        self._atualizar_status()

    def _atualizar_status(self) -> None:
        partes = [
            f"V3: {len(self._v3_filtrados)}/{len(self._v3)}",
            f"PHC: {len(self._phc_filtrados)}/{len(self._phc)}",
        ]
        if self._referencias_todas:
            partes.append(
                f"Placas: {len(self._referencias_filtradas)}/"
                f"{len(self._referencias_todas)}"
            )
        if not self._phc:
            partes.append("(carregue o PHC para incluir artigos PHC)")
        self.status_label.setText("   *   ".join(partes))

    @staticmethod
    def _escrever_linha(tabela: QTableWidget, row_index: int, valores: list[str]) -> None:
        for col, valor in enumerate(valores):
            item = QTableWidgetItem(valor)
            item.setBackground(QColor(tema.cor_zebra(row_index)))
            tabela.setItem(row_index, col, item)

    def _preencher_v3(self, materias: list) -> None:
        self.v3_table.setRowCount(len(materias))
        for row_index, materia in enumerate(materias):
            valores = [
                (materia.ref_le or "").strip(),
                (materia.referencia_fornecedor or "").strip(),
                (materia.descricao or "").strip(),
                format_currency(materia.preco_tabela),
                formatar_percentagem(normalize_percentagem_humana(materia.margem)),
                formatar_percentagem(normalize_percentagem_humana(materia.desconto)),
                format_currency(materia.preco_liquido),
                (materia.unidade or "").strip(),
                (materia.coresp_orla_0_4 or "").strip(),
                (materia.coresp_orla_1_0 or "").strip(),
                format_quantity(materia.comprimento),
                format_quantity(materia.largura),
                format_quantity(materia.espessura),
                (materia.fornecedor or "").strip(),
                _data_curta(getattr(materia, "updated_at", None)),
            ]
            self._escrever_linha(self.v3_table, row_index, valores)
        if not self._v3_restaurado and not self._v3_seed and materias:
            self.v3_table.resizeColumnsToContents()
            self._v3_seed = True

    def _preencher_phc(self, linhas: list[dict]) -> None:
        self.phc_table.setRowCount(len(linhas))
        for row_index, linha in enumerate(linhas):
            valores = [
                str(linha.get("Ref") or "").strip(),
                str(linha.get("Ref_Fornecedor") or "").strip(),
                str(linha.get("Descricao") or "").strip(),
                str(linha.get("Familia_Nome") or linha.get("Familia") or "").strip(),
                str(linha.get("Fornecedor") or "").strip(),
                format_currency(linha.get("Preco_Custo")),
                format_currency(linha.get("Preco_Ultimo")),
                str(linha.get("Unidade") or "").strip(),
                format_quantity(linha.get("Stock")),
                format_quantity(linha.get("Altura")),
                format_quantity(linha.get("Largura")),
                format_quantity(linha.get("Espessura")),
                str(linha.get("Data_Preco") or "").strip(),
                str(linha.get("Observacoes") or "").strip(),
            ]
            self._escrever_linha(self.phc_table, row_index, valores)
        if not self._phc_restaurado and not self._phc_seed and linhas:
            self.phc_table.resizeColumnsToContents()
            self._phc_seed = True

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
            precos = [referencia.precos.get(espessura, "") for espessura in ESPESSURAS]
            self._escrever_linha(self.referencias_table, row_index, base + precos)

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
        self.status_label.setText("A pesquisar nos cat\u00e1logos (IA)...")
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
            f'Cat\u00e1logos: {len(resultados)} resultados para "{texto}".'
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

    def gerar_resposta(self) -> None:
        pergunta = self.campo_pesquisa.texto().strip()
        if not pergunta:
            self.status_label.setText("Escreva uma pergunta no campo de pesquisa.")
            return
        v3 = self._v3_filtrados[:8]
        phc = self._phc_filtrados[:8]
        refs = self._referencias_filtradas[:10]
        trechos = self._ultimos_catalogos[:8]
        if not v3 and not phc and not refs and not trechos:
            self.status_label.setText(
                "Sem dados - pesquise primeiro (e carregue o PHC / cat\u00e1logos)."
            )
            return

        partes: list[str] = []
        linhas_artigos: list[str] = []
        for materia in v3:
            linhas_artigos.append(
                f"- [V3] {(materia.ref_le or '').strip()}: "
                f"{(materia.descricao or '').strip()} "
                f"| fab. {(materia.fornecedor or '').strip()} "
                f"| pre\u00e7o l\u00edq {format_currency(materia.preco_liquido)} "
                f"| {format_quantity(materia.comprimento)}x"
                f"{format_quantity(materia.largura)}x"
                f"{format_quantity(materia.espessura)} "
                f"| orla 0.4 {(materia.coresp_orla_0_4 or '').strip()} "
                f"| orla 1.0 {(materia.coresp_orla_1_0 or '').strip()}"
            )
        for linha in phc:
            linhas_artigos.append(
                f"- [PHC] {str(linha.get('Ref') or '').strip()}: "
                f"{str(linha.get('Descricao') or '').strip()} "
                f"| {str(linha.get('Familia_Nome') or '').strip()} "
                f"| {str(linha.get('Fornecedor') or '').strip()} "
                f"| custo {format_currency(linha.get('Preco_Custo'))} "
                f"| \u00falt. venda {format_currency(linha.get('Preco_Ultimo'))} "
                f"| {format_quantity(linha.get('Altura'))}x"
                f"{format_quantity(linha.get('Largura'))}x"
                f"{format_quantity(linha.get('Espessura'))}"
            )
        if linhas_artigos:
            partes.append(
                "ARTIGOS (mat\u00e9rias-primas V3/PHC):\n"
                + "\n".join(linhas_artigos)
            )

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
                f"[{index}] ({resultado.ficheiro} \u00b7 {resultado.local}) "
                f"{resultado.trecho}"
                for index, resultado in enumerate(trechos, start=1)
            ]
            partes.append("TRECHOS DE CAT\u00c1LOGOS:\n" + "\n".join(linhas))

        contexto = "\n\n".join(partes)
        self._iniciar_geracao(pergunta, contexto)

    def _iniciar_geracao(self, pergunta: str, contexto: str) -> None:
        if self._resposta_thread is not None:
            return
        self.resposta_text.clear()
        self.status_label.setText("A gerar resposta IA...")
        self.resposta_button.setEnabled(False)

        self._resposta_thread = QThread(self)
        self._resposta_worker = _RespostaWorker(pergunta, contexto)
        self._resposta_worker.moveToThread(self._resposta_thread)
        self._resposta_thread.started.connect(self._resposta_worker.run)
        self._resposta_worker.pedaco.connect(self._acrescentar_resposta)
        self._resposta_worker.falhou.connect(self._resposta_falhou)
        self._resposta_worker.concluido.connect(self._resposta_concluida)
        self._resposta_worker.falhou.connect(self._resposta_thread.quit)
        self._resposta_worker.concluido.connect(self._resposta_thread.quit)
        self._resposta_thread.finished.connect(self._resposta_worker.deleteLater)
        self._resposta_thread.finished.connect(self._resposta_thread.deleteLater)
        self._resposta_thread.finished.connect(self._finalizar_geracao)
        self._resposta_thread.start()

    def _acrescentar_resposta(self, texto: str) -> None:
        self.resposta_text.moveCursor(QTextCursor.MoveOperation.End)
        self.resposta_text.insertPlainText(texto)

    def _resposta_falhou(self, mensagem: str) -> None:
        self.status_label.setText(f"Erro a gerar resposta: {mensagem}")

    def _resposta_concluida(self) -> None:
        if not self.resposta_text.toPlainText().strip():
            self.resposta_text.setPlainText("(sem resposta)")
        self.status_label.setText("Resposta gerada.")

    def _finalizar_geracao(self) -> None:
        self._resposta_thread = None
        self._resposta_worker = None
        self.resposta_button.setEnabled(True)


def _data_curta(valor) -> str:
    if valor is None:
        return ""
    try:
        return valor.strftime("%d-%m-%Y")
    except (AttributeError, ValueError):
        return str(valor)


def _normalizar(value: object) -> str:
    if value is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(value))
    texto = "".join(
        caractere for caractere in texto if not unicodedata.combining(caractere)
    )
    return re.sub(r"[^a-z0-9]+", " ", texto.lower()).strip()


def _v3_corresponde(materia, texto: str) -> bool:
    tokens = _normalizar(texto).split()
    if not tokens:
        return True
    alvo = _normalizar(
        " ".join(
            [
                getattr(materia, "ref_le", None) or "",
                getattr(materia, "referencia_fornecedor", None) or "",
                getattr(materia, "descricao", None) or "",
                getattr(materia, "fornecedor", None) or "",
                getattr(materia, "coresp_orla_0_4", None) or "",
                getattr(materia, "coresp_orla_1_0", None) or "",
            ]
        )
    )
    return all(token in alvo for token in tokens)


def _phc_corresponde(linha: dict, texto: str) -> bool:
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
                "Familia",
                "Fornecedor",
                "Ref_Fornecedor",
            )
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
