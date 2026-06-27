"""Page "Ponto Situacao": production dashboard."""

from __future__ import annotations

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSeries,
    QBarSet,
    QChart,
    QChartView,
    QHorizontalBarSeries,
    QPieSeries,
    QValueAxis,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.domain.producao_estados import ESTADOS_PRODUCAO
from app.services.producao_dashboard_service import calcular_dashboard
from app.ui import tema
from app.ui.widgets.barra_cabecalho import BarraCabecalho
from app.ui.widgets.barra_pesquisa import CampoPesquisa

CORES_ESTADO = {
    "Desenho": "#2A78D6",
    "Produ\u00e7\u00e3o": "#EDA100",
    "Producao": "#EDA100",
    "Finalizado": "#1BAF7A",
    "Arquivado": "#888780",
}


class PontoSituacaoPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._kpis: dict[str, QLabel] = {}

        self.cabecalho = BarraCabecalho(
            "Ponto Situa\u00e7\u00e3o",
            ["Estado das obras em produ\u00e7\u00e3o"],
        )

        self.campo_pesquisa = CampoPesquisa()
        self.campo_pesquisa.pesquisa_mudou.connect(self._carregar)
        self.campo_pesquisa.limpar_clicado.connect(self._limpar_filtros)

        self.utilizador_combo = QComboBox()
        self.cliente_combo = QComboBox()
        self.estado_combo = QComboBox()
        for combo in (self.utilizador_combo, self.cliente_combo, self.estado_combo):
            combo.currentTextChanged.connect(self._carregar)

        self.atualizar_button = QPushButton("Atualizar")
        self.atualizar_button.setToolTip("Recalcular o dashboard")
        self.atualizar_button.clicked.connect(self._carregar)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.campo_pesquisa, stretch=1)
        toolbar.addWidget(QLabel("Utilizador"))
        toolbar.addWidget(self.utilizador_combo)
        toolbar.addWidget(QLabel("Cliente"))
        toolbar.addWidget(self.cliente_combo)
        toolbar.addWidget(QLabel("Estado"))
        toolbar.addWidget(self.estado_combo)
        toolbar.addWidget(self.atualizar_button)

        self.atualizado_label = QLabel("")
        self.atualizado_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO};")

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(10)
        for chave, titulo, cor in (
            ("total", "Total obras", None),
            ("desenho", "Em desenho", None),
            ("producao", "Em produ\u00e7\u00e3o", None),
            ("atrasadas", "Atrasadas", "#A32D2D"),
            ("finalizadas", "Finalizadas", None),
            ("valor", "Valor em aberto", None),
            ("sem_preco", "Sem pre\u00e7o", "#854F0B"),
        ):
            card, valor = self._criar_kpi(titulo, cor)
            self._kpis[chave] = valor
            kpi_row.addWidget(card)

        self.estado_box = QVBoxLayout()
        self.responsavel_box = QVBoxLayout()
        self.clientes_box = QVBoxLayout()

        w_estado = QWidget()
        w_estado.setLayout(self.estado_box)
        w_resp = QWidget()
        w_resp.setLayout(self.responsavel_box)
        w_cli = QWidget()
        w_cli.setLayout(self.clientes_box)

        topo_graf = QHBoxLayout()
        topo_graf.addWidget(w_estado, stretch=1)
        topo_graf.addWidget(w_resp, stretch=1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)
        layout.addWidget(self.cabecalho)
        layout.addLayout(toolbar)
        layout.addWidget(self.atualizado_label)
        layout.addLayout(kpi_row)
        layout.addLayout(topo_graf, stretch=1)
        layout.addWidget(w_cli, stretch=1)

        self._carregar()

    def _criar_kpi(self, titulo, cor=None):
        card = QFrame()
        card.setStyleSheet(
            f"QFrame {{ background: {tema.BEGE_AREIA}; border-radius: 8px; }}"
        )
        lay = QVBoxLayout(card)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(2)

        titulo_label = QLabel(titulo)
        titulo_label.setStyleSheet(f"color: {tema.CASTANHO_MEDIO}; font-size: 12px;")

        valor_label = QLabel("-")
        valor_label.setStyleSheet(
            f"color: {cor or tema.CASTANHO_ESCURO}; "
            "font-size: 22px; font-weight: bold;"
        )

        lay.addWidget(titulo_label)
        lay.addWidget(valor_label)
        return card, valor_label

    def _carregar(self, *_args) -> None:
        texto = self.campo_pesquisa.texto()
        utilizador = self._combo_valor(self.utilizador_combo)
        cliente = self._combo_valor(self.cliente_combo)
        estado = self._combo_valor(self.estado_combo)

        try:
            with SessionLocal() as session:
                dados = calcular_dashboard(
                    session,
                    texto=texto,
                    utilizador=utilizador,
                    cliente=cliente,
                    estado=estado,
                )
                opcoes = (
                    dados
                    if not any((texto, utilizador, cliente, estado))
                    else calcular_dashboard(session)
                )
        except SQLAlchemyError:
            self.atualizado_label.setText(
                "N\u00e3o foi poss\u00edvel carregar o dashboard."
            )
            return

        self._atualizar_combos(opcoes)

        self._kpis["total"].setText(str(dados.total))
        self._kpis["desenho"].setText(str(dados.em_desenho))
        self._kpis["producao"].setText(str(dados.em_producao))
        self._kpis["atrasadas"].setText(str(dados.atrasadas))
        self._kpis["finalizadas"].setText(str(dados.finalizadas))
        self._kpis["valor"].setText(
            f"{dados.valor_aberto:,.0f} \u20ac".replace(",", ".")
        )
        self._kpis["sem_preco"].setText(str(dados.sem_preco))

        self._substituir(self.estado_box, self._grafico_estado(dados))
        self._substituir(self.responsavel_box, self._grafico_responsavel(dados))
        self._substituir(self.clientes_box, self._grafico_clientes(dados))
        self.atualizado_label.setText(
            f"{dados.total} obras \u00b7 atualizado {dados.hoje.strftime('%d-%m-%Y')}"
        )

    def _limpar_filtros(self) -> None:
        widgets = (
            self.campo_pesquisa,
            self.utilizador_combo,
            self.cliente_combo,
            self.estado_combo,
        )
        estados_sinais = [(widget, widget.blockSignals(True)) for widget in widgets]
        self.campo_pesquisa.limpar()
        for combo in (self.utilizador_combo, self.cliente_combo, self.estado_combo):
            if combo.count():
                combo.setCurrentIndex(0)
        for widget, estado_anterior in estados_sinais:
            widget.blockSignals(estado_anterior)
        self._carregar()

    def _atualizar_combos(self, dados) -> None:
        self._popular_combo(
            self.utilizador_combo,
            [valor for valor, _qt in dados.por_responsavel],
        )
        self._popular_combo(
            self.cliente_combo,
            [valor for valor, _qt in dados.por_cliente],
        )
        self._popular_combo(
            self.estado_combo,
            self._combinar_valores(
                list(ESTADOS_PRODUCAO),
                [valor for valor, _qt in dados.por_estado],
            ),
        )

    def _substituir(self, box, widget) -> None:
        while box.count():
            item = box.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        box.addWidget(widget)

    def _grafico_estado(self, dados):
        serie = QPieSeries()
        serie.setHoleSize(0.45)
        for estado, qt in dados.por_estado:
            fatia = serie.append(f"{estado} ({qt})", qt)
            fatia.setBrush(QColor(CORES_ESTADO.get(estado, tema.CINZA_CASTANHO)))
            fatia.setLabelVisible(True)

        chart = QChart()
        chart.addSeries(serie)
        chart.setTitle("Obras por estado")
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignRight)
        return self._chart_view(chart)

    def _grafico_responsavel(self, dados):
        top = dados.por_responsavel[:10]
        barset = QBarSet("Obras")
        categorias = []
        for responsavel, qt in top:
            barset.append(qt)
            categorias.append(responsavel)
        barset.setColor(QColor(tema.CASTANHO_MEDIO))

        serie = QBarSeries()
        serie.append(barset)

        chart = QChart()
        chart.addSeries(serie)
        chart.setTitle("Obras por respons\u00e1vel")

        eixo_x = QBarCategoryAxis()
        eixo_x.append(categorias)
        chart.addAxis(eixo_x, Qt.AlignmentFlag.AlignBottom)
        serie.attachAxis(eixo_x)

        eixo_y = QValueAxis()
        eixo_y.applyNiceNumbers()
        chart.addAxis(eixo_y, Qt.AlignmentFlag.AlignLeft)
        serie.attachAxis(eixo_y)

        chart.legend().setVisible(False)
        return self._chart_view(chart)

    def _grafico_clientes(self, dados):
        top = dados.por_cliente[:8]
        barset = QBarSet("Obras")
        categorias = []
        for cliente, qt in reversed(top):
            barset.append(qt)
            nome = cliente if len(cliente) <= 24 else cliente[:23] + "..."
            categorias.append(nome)
        barset.setColor(QColor("#1BAF7A"))

        serie = QHorizontalBarSeries()
        serie.append(barset)

        chart = QChart()
        chart.addSeries(serie)
        chart.setTitle("Top clientes (n\u00ba de obras)")

        eixo_y = QBarCategoryAxis()
        eixo_y.append(categorias)
        chart.addAxis(eixo_y, Qt.AlignmentFlag.AlignLeft)
        serie.attachAxis(eixo_y)

        eixo_x = QValueAxis()
        eixo_x.applyNiceNumbers()
        chart.addAxis(eixo_x, Qt.AlignmentFlag.AlignBottom)
        serie.attachAxis(eixo_x)

        chart.legend().setVisible(False)
        return self._chart_view(chart)

    @staticmethod
    def _chart_view(chart):
        chart.setBackgroundVisible(False)
        view = QChartView(chart)
        view.setRenderHint(QPainter.RenderHint.Antialiasing)
        view.setMinimumHeight(220)
        return view

    def _popular_combo(self, combo, valores) -> None:
        atual = combo.currentText() or "Todos"
        estado_anterior = combo.blockSignals(True)
        combo.clear()
        combo.addItem("Todos")
        for valor in valores:
            if valor and valor not in ("(sem resp)", "(sem cliente)", "(sem estado)"):
                combo.addItem(valor)

        indice = combo.findText(atual)
        combo.setCurrentIndex(indice if indice >= 0 else 0)
        combo.blockSignals(estado_anterior)

    @staticmethod
    def _combo_valor(combo):
        valor = combo.currentText().strip()
        return None if (not valor or valor == "Todos") else valor

    @staticmethod
    def _combinar_valores(primeiros: list[str], restantes: list[str]) -> list[str]:
        valores: list[str] = []
        vistos: set[str] = set()
        for valor in [*primeiros, *restantes]:
            chave = valor.strip().lower()
            if not chave or chave in vistos:
                continue
            valores.append(valor)
            vistos.add(chave)
        return valores
