"""Pesquisa IA - fontes: Materias-Primas do V3 (local) + PHC (artigos ST)."""

from __future__ import annotations
from app.domain.pesquisa_ia_resumo import resumo_fontes, comentario_html

import re
import unicodedata

from PySide6.QtCore import QObject, Qt, QThread, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
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
from sqlalchemy.orm import Session
from pathlib import Path
from app.ui.helpers.pesquisa_ia_fluxo import PesquisaIAFluxo, CicloPesquisa
from app.domain.pesquisa_ia_consulta import corresponde, mesma_espessura, termos, observacoes_relevantes
from app.services.system_setting_service import SystemSettingService

from app.db.session import SessionLocal
from app.domain.numeros import formatar_percentagem, normalize_percentagem_humana
from app.services.def_materia_prima_service import DefMateriaPrimaService
from app.services.phc_materiais_service import query_phc_materiais
from app.services.placas_referencias_service import LinhaReferencia, listar_referencias
from app.services.pesquisa_ia_resposta_service import RespostaIAService
from app.services.pesquisa_ia_search_service import PesquisaCatalogosService
from app.ui.helpers.painel_recolhivel import PainelRecolhivel
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
    cabecalho.setStyleSheet(tema.ESTILO_CABECALHO_VISTAS_DADOS)
    restaurado = ligar_persistencia_larguras(tabela, chave)
    return tabela, restaurado


def _ficha(texto: str) -> QPushButton:
    """Um contador clicavel para a barra de cima.

    Diz quantos resultados ha' em cada tabela ANTES de se abrir seja o que
    for, e leva la' quem carregar nele.
    """
    botao = QPushButton(texto)
    botao.setFlat(True)
    botao.setCursor(Qt.CursorShape.PointingHandCursor)
    botao.setStyleSheet(
        "QPushButton {"
        f" border: 1px solid {tema.CINZA_CASTANHO}; border-radius: 10px;"
        f" padding: 3px 11px; color: {tema.TEXTO_NORMAL}; text-align: left; }}"
        f"QPushButton:hover {{ background-color: {tema.BEGE_AREIA}; }}"
        f"QPushButton:disabled {{ color: {tema.CINZA_ESCURO};"
        f" border-color: {tema.CINZA_SUAVE}; }}"
    )
    return botao


def montar_fontes(v3, phc, refs, trechos) -> str:
    """De onde vieram os valores que o modelo teve a` frente.

    Nao se pede isto ao modelo: um modelo pequeno inventa a fonte com a mesma
    facilidade com que inventa o preco. Esta lista e' montada com o que
    REALMENTE lhe foi entregue, por isso ou esta' certa ou nao aparece.
    """
    linhas: list[str] = []

    referencias_v3 = [
        (materia.ref_le or "").strip() for materia in v3 if (materia.ref_le or "").strip()
    ]
    if referencias_v3:
        linhas.append("Matérias-primas V3: " + " | ".join(referencias_v3))

    referencias_phc = [
        str(linha.get("Ref") or "").strip()
        for linha in phc
        if str(linha.get("Ref") or "").strip()
    ]
    if referencias_phc:
        linhas.append("PHC: " + " | ".join(referencias_phc))

    # Uma referencia de placa aparece em varias folhas (EGGER, stock do B&F,
    # stock da WoodSide) com precos diferentes -- e saber de QUAL folha veio o
    # preco e' precisamente o que o Paulo precisa.
    folhas_por_referencia: dict[str, list[str]] = {}
    for referencia in refs:
        nome = (referencia.referencia or "").strip()
        folha = (referencia.folha or "").strip()
        if not nome:
            continue
        folhas = folhas_por_referencia.setdefault(nome, [])
        if folha and folha not in folhas:
            folhas.append(folha)
    if folhas_por_referencia:
        partes = [
            f"{nome} ({' | '.join(folhas)})" if folhas else nome
            for nome, folhas in folhas_por_referencia.items()
        ]
        linhas.append("Referências de placas: " + " | ".join(partes))

    locais_por_ficheiro: dict[str, list[str]] = {}
    for resultado in trechos:
        ficheiro = (resultado.ficheiro or "").strip() or "(sem ficheiro)"
        local = (resultado.local or "").strip()
        locais = locais_por_ficheiro.setdefault(ficheiro, [])
        if local and local not in locais:
            locais.append(local)
    for ficheiro, locais in locais_por_ficheiro.items():
        linhas.append(
            f"{ficheiro} ({' | '.join(locais)})" if locais else ficheiro
        )

    if not linhas:
        return ""
    marcadores = [f"• {linha}" for linha in linhas]
    return "\n\nFontes:\n" + "\n".join(marcadores)


class _RespostaWorker(QObject):
    """Gera a resposta IA fora da thread da UI, emitindo pedacos (streaming)."""

    pedaco = Signal(str)
    falhou = Signal(str)
    concluido = Signal()

    def __init__(self, pergunta: str, contexto: str) -> None:
        super().__init__()
        self._pergunta = pergunta
        self._contexto = contexto
        self._engine = SessionLocal.kw.get("bind")

    def run(self) -> None:
        try:
            with Session(bind=self._engine) as session:
                servico = RespostaIAService(session)
                for pedaco in servico.gerar_stream(self._pergunta, self._contexto):
                    if QThread.currentThread().isInterruptionRequested():
                        break
                    self.pedaco.emit(pedaco)
        except Exception as exc:  # noqa: BLE001
            self.falhou.emit(str(exc))
            return
        self.concluido.emit()


class PesquisaIAPage(PesquisaIAFluxo, QWidget):
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
        #: A pergunta a que os catalogos em cima pertencem. Sem isto os
        #: resultados ficavam presos: escrevia-se outra referencia e a
        #: tabela continuava com a anterior -- e a resposta IA era gerada
        #: com os catalogos do artigo errado, sem ninguem dar por isso.
        self._texto_catalogos: str = ""
        #: As fontes da ultima resposta, acrescentadas no fim quando ela
        #: acaba de ser escrita.
        self._fontes: str = ""
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

        # A resposta e' o que se le' primeiro, por isso fica em cima. Antes
        # estava no fundo, depois de quatro tabelas -- era preciso percorrer a
        # pagina toda para chegar aquilo que se tinha ido buscar.
        # Fechada enquanto nao houver resposta: uma caixa de texto vazia a
        # ocupar um terco do ecra' era exatamente o que tornava esta pagina
        # pesada. Abre-se sozinha quando a resposta comeca a ser escrita.
        self.painel_resposta = PainelRecolhivel(
            "Resposta IA (com cita\u00e7\u00f5es e fontes)",
            self.resposta_text,
            aberto=False,
            com_botao_grande=False,
        )
        self.painel_v3 = PainelRecolhivel(
            "Mat\u00e9rias-primas do V3 (interno)", self.v3_table
        )
        self.painel_phc = PainelRecolhivel(
            "Artigos PHC (Ferragens, Madeiras, Orlas)", self.phc_table
        )
        self.painel_referencias = PainelRecolhivel(
            "Refer\u00eancias de placas (cat\u00e1logo curado)", self.referencias_table
        )
        self.painel_catalogos = PainelRecolhivel(
            "Cat\u00e1logos (documentos) \u2014 duplo-clique abre o ficheiro",
            self.catalogo_table,
        )
        self._paineis = [
            self.painel_resposta,
            self.painel_v3,
            self.painel_phc,
            self.painel_referencias,
            self.painel_catalogos,
        ]
        for painel in self._paineis:
            painel.grande_pedido.connect(self._alternar_painel_grande)

        self.fichas: dict[str, QPushButton] = {}
        linha_fichas = QHBoxLayout()
        linha_fichas.setSpacing(6)
        for chave, painel in (
            ("v3", self.painel_v3),
            ("phc", self.painel_phc),
            ("placas", self.painel_referencias),
            ("catalogos", self.painel_catalogos),
        ):
            ficha = _ficha("")
            ficha.clicked.connect(
                lambda _=False, alvo=painel: self._mostrar_painel(alvo)
            )
            self.fichas[chave] = ficha
            linha_fichas.addWidget(ficha)
        linha_fichas.addStretch()

        self.tabelas_splitter = QSplitter(Qt.Orientation.Vertical)
        self.tabelas_splitter.setChildrenCollapsible(False)
        for painel in self._paineis:
            self.tabelas_splitter.addWidget(painel)
        for indice, fator in enumerate((1, 2, 2, 2, 2)):
            self.tabelas_splitter.setStretchFactor(indice, fator)
        # Chave nova: a ordem dos paineis mudou (a resposta subiu para o
        # primeiro), e as alturas guardadas da ordem antiga davam um arranjo
        # sem sentido a quem ja' usava a pagina.
        ligar_persistencia_splitter(self.tabelas_splitter, "pesquisa_ia_paineis")

        layout = QVBoxLayout()
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)
        layout.addWidget(self.cabecalho)
        layout.addLayout(toolbar)
        layout.addLayout(linha_fichas)
        layout.addWidget(self.status_label)
        layout.addWidget(self.tabelas_splitter, stretch=1)
        self.setLayout(layout)

        self.preparar_fluxo(layout, toolbar, linha_fichas)

    def carregar_v3(self) -> None:
        self.ler_fonte("v3", lambda session: DefMateriaPrimaService(session).listar_materias_primas())

    def carregar_phc(self) -> None:
        self.ler_fonte("phc", query_phc_materiais)

    def carregar_referencias(self) -> None:
        def ler(session):
            pasta = SystemSettingService(session).obter_valor("pasta_pesquisa_profunda_ia", "") or ""
            ficheiro = Path(pasta) / "12_Placas_Referencias_COMPLETO.xlsx"
            stat = ficheiro.stat()
            assinatura = (str(ficheiro), stat.st_mtime_ns, stat.st_size)
            if self._cache_refs is None or self._cache_refs[0] != assinatura:
                self._cache_refs = (assinatura, listar_referencias(session))
            return self._cache_refs[1]
        self.ler_fonte("placas", ler)

    def aplicar_pesquisa(self, _text: str | None = None) -> None:
        texto = self.campo_pesquisa.texto()
        if texto.strip():
            self._v3_filtrados = [
                materia for materia in self._v3 if _v3_corresponde(materia, texto) and mesma_espessura(materia.espessura, texto, self.espessura_input.currentData())
            ]
            self._phc_filtrados = [
                linha for linha in self._phc if _phc_corresponde(linha, texto) and mesma_espessura(linha.get("Espessura"), texto, self.espessura_input.currentData())
            ]
            self._referencias_filtradas = [
                referencia
                for referencia in self._referencias_todas
                if _ref_corresponde(referencia, texto)
            ]
        else:
            self._v3_filtrados = [m for m in self._v3 if mesma_espessura(m.espessura, texto, self.espessura_input.currentData())]
            self._phc_filtrados = [r for r in self._phc if mesma_espessura(r.get("Espessura"), texto, self.espessura_input.currentData())]
            self._referencias_filtradas = self._referencias_todas

        if texto.strip() != self._texto_catalogos:
            self._esquecer_catalogos()

        self._preencher_v3(self._v3_filtrados)
        self._preencher_phc(self._phc_filtrados)
        self._preencher_referencias(self._referencias_filtradas)
        self._atualizar_status()
        self.atualizar_resultados_unificados()

    def _esquecer_catalogos(self) -> None:
        """Deitar fora os catalogos da pergunta anterior.

        As materias-primas e o PHC voltam a filtrar-se sozinhos enquanto se
        escreve; os catalogos nao, porque a pesquisa por IA e' lenta e so' corre
        a pedido. Por isso a tabela tem de ficar VAZIA em vez de ficar
        desatualizada -- vazia percebe-se, desatualizada engana.
        """
        self._ultimos_catalogos = []
        self._texto_catalogos = ""
        self.catalogo_table.setRowCount(0)

    def _mostrar_painel(self, painel: PainelRecolhivel) -> None:
        """Abrir um painel a partir da ficha que o conta."""
        self.resultados_tabs.setCurrentWidget(painel)
        if not painel.esta_aberto():
            painel.abrir(True)

    def _alternar_painel_grande(self, painel: PainelRecolhivel) -> None:
        """Dar o ecrã só a esta tabela, ou devolver tudo ao normal.

        Serve para percorrer os 17 artigos do PHC sem andar aos saltos entre
        quatro tabelas espremidas.
        """
        voltar = painel.em_grande()
        for outro in self._paineis:
            outro.definir_em_grande(False)
        if voltar:
            self._arrumar_paineis()
            return

        painel.definir_em_grande(True)
        for outro in self._paineis:
            outro.abrir(outro is painel)

    def _arrumar_paineis(self) -> None:
        """Voltar ao arranjo normal: aberto o que tem alguma coisa para mostrar."""
        self._atualizar_status()
        self.painel_resposta.abrir(bool(self.resposta_text.toPlainText().strip()))

    def _atualizar_status(self) -> None:
        """Escrever as contagens nas fichas e nos títulos dos painéis."""
        self.painel_v3.definir_contagem(
            len(self._v3_filtrados),
            len(self._v3),
            texto_vazio=(
                "Nenhuma matéria-prima do V3 corresponde à pesquisa. "
                "Pode existir no PHC ou nos catálogos dos fornecedores."
            ),
        )
        self.painel_phc.definir_contagem(
            len(self._phc_filtrados),
            len(self._phc),
            texto_vazio=(
                "PHC ainda sem dados disponíveis — consulte o estado das fontes. "
                "Atualizar fontes permite tentar novamente."
                if not self._phc
                else "Nenhum artigo do PHC corresponde à pesquisa."
            ),
        )
        self.painel_referencias.definir_contagem(
            len(self._referencias_filtradas),
            len(self._referencias_todas),
            texto_vazio=(
                "Referências ainda sem dados disponíveis — consulte o estado das fontes. "
                "Atualizar fontes permite tentar novamente."
                if not self._referencias_todas
                else (
                    "Nenhuma referência de placa corresponde à pesquisa. "
                    "Este catálogo curado só tem Finsa, Fiware e EGGER."
                )
            ),
        )
        exatos = sum(1 for resultado in self._ultimos_catalogos if resultado.exato)
        self.painel_catalogos.definir_contagem(
            len(self._ultimos_catalogos),
            detalhe=f"{exatos} exactos" if exatos else "",
            texto_vazio=(
                "Escreva uma pesquisa para procurar automaticamente nos "
                "catálogos e tabelas dos fornecedores."
            ),
        )

        self.fichas["v3"].setText(
            f"Matérias-primas V3   {len(self._v3_filtrados)}"
        )
        self.fichas["phc"].setText(f"Artigos PHC   {len(self._phc_filtrados)}")
        self.fichas["placas"].setText(
            f"Referências de placas   {len(self._referencias_filtradas)}"
        )
        self.fichas["catalogos"].setText(
            f"Catálogos   {len(self._ultimos_catalogos)}"
        )
        for chave, quantos in (
            ("v3", len(self._v3_filtrados)),
            ("phc", len(self._phc_filtrados)),
            ("placas", len(self._referencias_filtradas)),
            ("catalogos", len(self._ultimos_catalogos)),
        ):
            self.fichas[chave].setEnabled(quantos > 0)

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
            return
        token = self.chave_consulta()
        engine = SessionLocal.kw.get("bind")
        def ler():
            with Session(bind=engine) as session:
                svc = SystemSettingService(session)
                pasta = svc.obter_valor("pasta_embeddings_ia", "") or ""
                modelo = svc.obter_valor("modelo_embeddings_ia", "") or ""
                base = Path(pasta)
                assinatura = (pasta, modelo, tuple((p.stat().st_mtime_ns, p.stat().st_size)
                    for p in (base / "meta.jsonl", base / "embeddings.npy")))
                if self._cache_cat is None or self._cache_cat[0] != assinatura:
                    self._cache_cat = (assinatura, PesquisaCatalogosService(session))
                servico = self._cache_cat[1]
            motivo = servico.motivo_indisponivel()
            if motivo:
                raise RuntimeError(motivo)
            return servico.pesquisar(texto, top_n=30)
        self._iniciar_fonte("catalogos", ler, token)

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
                if not resultado.exato:
                    # A pesquisa devolve sempre 30 resultados; os que nao tem
                    # o que foi pedido sao o vizinho mais parecido. Ficam
                    # esbatidos e nao entram na resposta -- ve^-se logo que
                    # estao ali so' para consulta.
                    item.setForeground(QColor(tema.CINZA_ESCURO))
                    item.setToolTip(
                        "Aproximação: não contém o que pesquisou, "
                        "por isso não entra na resposta IA."
                    )
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
        if not termos(pergunta):
            self.status_label.setText("Indique uma referência, material ou fornecedor para preparar a resposta.")
            return
        if self._resposta_thread is not None:
            self._resposta_pendente = self.chave_consulta()
            return
        v3 = self._v3_filtrados[:8]
        phc = self._phc_filtrados[:8]
        refs = self._referencias_filtradas[:10]
        # So' os trechos que contem MESMO o que foi pedido. A pesquisa devolve
        # sempre 30 resultados, e os que sobram sao o vizinho mais parecido --
        # placas de outra cor, acessorios de outra familia. Entregues ao modelo
        # em pe' de igualdade, ele respondia sobre esses.
        exatos = [resultado for resultado in self._ultimos_catalogos if resultado.exato]
        trechos = exatos[:8]
        if not v3 and not phc and not refs and not trechos and not self._woodstore_filtrados:
            self.status_label.setText(
                "Sem dados - pesquise primeiro (e carregue o PHC / cat\u00e1logos)."
            )
            return

        self._resumo_html = resumo_fontes(self._v3_filtrados, self._phc_filtrados, self._woodstore_filtrados, self._referencias_filtradas, exatos, self.fontes_status.text())
        self._fontes = montar_fontes(v3, phc, refs, trechos)

        partes: list[str] = []
        linhas_artigos: list[str] = []
        for materia in v3:
            linhas_artigos.append(
                f"- [V3] {(materia.ref_le or '').strip()}: "
                f"{(materia.descricao or '').strip()} "
                f"| fornecedor {(materia.fornecedor or '').strip()} "
                f"| pre\u00e7o l\u00edq {format_currency(materia.preco_liquido)} "
                f"| {format_quantity(materia.comprimento)}x"
                f"{format_quantity(materia.largura)}x"
                f"{format_quantity(materia.espessura)} "
                f"| orla 0.4 {(materia.coresp_orla_0_4 or '').strip()} "
                f"| orla 1.0 {(materia.coresp_orla_1_0 or '').strip()} "
                f"| unidade {materia.unidade or ''} "
                f"| data preço {_data_curta(getattr(materia, 'data_ultimo_preco', None))} "
                f"| observações {observacoes_relevantes(materia.observacoes or '', pergunta)}"
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
                f"{format_quantity(linha.get('Espessura'))} "
                f"| unidade {linha.get('Unidade', '')} | stock PHC {linha.get('Stock', '')} "
                f"| data preço {linha.get('Data_Preco', '')}"
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

        wood = self._woodstore_filtrados[:12]
        if wood:
            partes.append("WOODSTORE (saldo calculado = contagem Lagen menos reservas; confirmar pacotes/divergências):\n" + "\n".join(
                f"{r.get('Referencia')}: {r.get('Material')} | código {r.get('Codigo')} | dimensões {r.get('Comprimento')}x{r.get('Largura')}x{r.get('Espessura')} mm | Lagen {r.get('Quantidade')} | reservas {r.get('Reservadas')} | saldo {r.get('Disponivel')}"
                for r in wood))
            self._fontes += "\nWoodStore: " + " | ".join(str(r.get('Referencia')) for r in wood)
        partes.append("ESTADO E MOMENTO DAS FONTES:\n" + self.fontes_status.text())
        partes.append("O contexto é uma seleção limitada de resultados; não afirmar inexistência global de stock. Não misturar preço líquido V3, custo PHC e preço de catálogo. Preservar unidade, acabamento e espessura.")
        contexto = "\n\n".join(partes)
        self._iniciar_geracao(pergunta, contexto)

    def _iniciar_geracao(self, pergunta: str, contexto: str) -> None:
        if self._resposta_thread is not None:
            return
        self._texto_llm = ""
        self.resposta_text.setHtml(getattr(self, "_resumo_html", "") + comentario_html("A preparar comentário…"))
        self.painel_resposta.abrir(True)
        self.status_label.setText("A gerar resposta IA...")
        self.resposta_button.setEnabled(False)

        self._consulta_resposta = self.chave_consulta()
        self._resposta_thread = QThread(QApplication.instance())
        self._resposta_worker = _RespostaWorker(pergunta, contexto)
        self._resposta_worker.moveToThread(self._resposta_thread)
        CicloPesquisa(self._resposta_thread, self._resposta_worker)
        self._resposta_thread.started.connect(self._resposta_worker.run)
        self._resposta_worker.pedaco.connect(self._receptor_pesquisa.pedaco, Qt.ConnectionType.QueuedConnection)
        self._resposta_worker.falhou.connect(self._receptor_pesquisa.falhou, Qt.ConnectionType.QueuedConnection)
        self._resposta_worker.concluido.connect(self._receptor_pesquisa.concluido, Qt.ConnectionType.QueuedConnection)
        self._resposta_worker.falhou.connect(self._resposta_thread.quit, Qt.ConnectionType.DirectConnection)
        self._resposta_worker.concluido.connect(self._resposta_thread.quit, Qt.ConnectionType.DirectConnection)
        self._resposta_thread.finished.connect(self._receptor_pesquisa.finalizado, Qt.ConnectionType.QueuedConnection)
        self._resposta_thread.start()

    def _acrescentar_resposta(self, texto: str) -> None:
        if self._consulta_resposta != self.chave_consulta():
            return
        self._texto_llm = getattr(self, "_texto_llm", "") + texto
        self.resposta_text.setHtml(getattr(self, "_resumo_html", "") + comentario_html(self._texto_llm))

    def _resposta_falhou(self, mensagem: str) -> None:
        if self._consulta_resposta != self.chave_consulta():
            return
        self.resposta_text.setHtml(getattr(self, "_resumo_html", "") + comentario_html("Comentário indisponível. Os dados das fontes permanecem acima."))
        self.status_label.setText(f"Erro a gerar resposta: {mensagem}")

    def _resposta_concluida(self) -> None:
        if self._consulta_resposta != self.chave_consulta():
            return
        self.resposta_text.setHtml(getattr(self, "_resumo_html", "") + comentario_html(getattr(self, "_texto_llm", "") or "Sem comentário gerado."))
        self.status_label.setText("Resposta gerada.")

    def _finalizar_geracao(self) -> None:
        self._resposta_thread = None
        self._resposta_worker = None
        self.resposta_button.setEnabled(True)
        if self._resposta_pendente == self.chave_consulta() and not self._jobs:
            self._resposta_pendente = None
            self.gerar_resposta()


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
    tokens = termos(texto)
    if not tokens:
        return True
    alvo = _normalizar(
        " ".join(
            [
                getattr(materia, "ref_le", None) or "",
                getattr(materia, "referencia_fornecedor", None) or "",
                getattr(materia, "descricao", None) or "",
                getattr(materia, "observacoes", None) or "",
                getattr(materia, "fornecedor", None) or "",
                getattr(materia, "coresp_orla_0_4", None) or "",
                getattr(materia, "coresp_orla_1_0", None) or "",
            ]
        )
    )
    return corresponde(alvo, texto)


def _phc_corresponde(linha: dict, texto: str) -> bool:
    tokens = termos(texto)
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
                "Observacoes",
            )
        )
    )
    return corresponde(alvo, texto)


def _ref_corresponde(referencia: LinhaReferencia, texto: str) -> bool:
    tokens = termos(texto)
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
    return corresponde(alvo, texto)
