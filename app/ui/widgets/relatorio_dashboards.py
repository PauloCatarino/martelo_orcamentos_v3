"""Dashboards (gráficos matplotlib embebidos) dos relatórios (fase 8W.3a/8W.3b).

Quatro gráficos de barras (placas / orlas / ferragens / máquinas) seguidos de um
gráfico de pizza da distribuição de custos, empilhados numa área de scroll
vertical. O matplotlib é opcional: quando não está instalado o widget mostra um
aviso em vez dos gráficos, para o resto da página de relatórios continuar a
funcionar. A modelação (pura) dos dados está em
:mod:`app.domain.relatorio_graficos`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from app.domain import relatorio_graficos
from app.ui import tema
from app.utils.formatters import format_currency

try:  # matplotlib é opcional (ver docstring do módulo).
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
except Exception:  # noqa: BLE001 — qualquer falha de import desativa os gráficos.
    FigureCanvas = Figure = None

# Cores das barras a partir da paleta Lança Encanto.
_COR_BARRA_1 = tema.CASTANHO_MEDIO
_COR_BARRA_2 = tema.CASTANHO_ESCURO

# Paleta da pizza: tons de app.ui.tema, uma cor por fatia (cicla se preciso).
_CORES_PIZZA = (
    tema.CASTANHO_ESCURO,
    tema.CASTANHO_MEDIO,
    tema.PLACA_INTEIRA_FUNDO,
    tema.BEGE_AREIA,
    tema.CINZA_CASTANHO,
    tema.BEGE_CLARO,
)

_MENSAGEM_SEM_MATPLOTLIB = "Instale matplotlib para ver os gráficos."

# Áreas de gráfico (chave interna -> título da secção), pela ordem de desenho.
_SECCOES = (
    ("placas", "Placas"),
    ("orlas", "Orlas"),
    ("ferragens", "Ferragens"),
    ("maquinas", "Máquinas / MO"),
    ("distribuicao", "Distribuição de Custos"),
)


class DashboardsWidget(QWidget):
    """Pilha vertical de quatro gráficos de barras + pizza de distribuição."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._canvases: dict[str, object] = {}

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        if FigureCanvas is None:
            # Sem matplotlib: mostra o aviso e não cria canvases.
            aviso = QLabel(_MENSAGEM_SEM_MATPLOTLIB)
            aviso.setWordWrap(True)
            aviso.setStyleSheet(
                f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 12px;"
            )
            layout.addWidget(aviso)
            layout.addStretch()
            self.setLayout(layout)
            return

        conteudo = QWidget()
        conteudo_layout = QVBoxLayout()
        conteudo_layout.setContentsMargins(0, 0, 0, 0)
        conteudo_layout.setSpacing(12)
        for chave, titulo in _SECCOES:
            conteudo_layout.addWidget(self._titulo_seccao(titulo))
            canvas = FigureCanvas(Figure(figsize=(6, 3)))
            self._canvases[chave] = canvas
            conteudo_layout.addWidget(canvas)
        conteudo_layout.addStretch()
        conteudo.setLayout(conteudo_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(conteudo)

        layout.addWidget(scroll, stretch=1)
        self.setLayout(layout)

    # ----- API pública -----

    def atualizar(self, resumo) -> None:
        """Redesenha os gráficos (4 barras + pizza) a partir de um ResumoConsumos."""
        if FigureCanvas is None:
            return
        self._desenhar(
            self._canvases["placas"],
            relatorio_graficos.dados_placas(resumo.placas),
        )
        self._desenhar(
            self._canvases["orlas"],
            relatorio_graficos.dados_orlas(resumo.orlas),
        )
        self._desenhar(
            self._canvases["ferragens"],
            relatorio_graficos.dados_ferragens(resumo.ferragens),
        )
        self._desenhar(
            self._canvases["maquinas"],
            relatorio_graficos.dados_maquinas(resumo.maquinas),
        )
        self._desenhar_pizza(
            self._canvases["distribuicao"],
            relatorio_graficos.dados_distribuicao(resumo.distribuicao),
        )

    # ----- Desenho -----

    def _desenhar(self, canvas, grafico) -> None:
        """Desenha um GraficoBarras (1 ou 2 séries) num canvas.

        1 série -> barras simples; 2 séries -> barras agrupadas (com offset) e
        legenda. Os Decimal são convertidos para float ao desenhar. Sem etiquetas
        -> texto centrado "Sem dados" (sem barras).
        """
        figura = canvas.figure
        figura.clear()
        eixo = figura.add_subplot(111)
        eixo.set_title(grafico.titulo, color=tema.CASTANHO_ESCURO)

        if not grafico.etiquetas:
            eixo.text(
                0.5, 0.5, "Sem dados",
                ha="center", va="center", transform=eixo.transAxes,
                color=tema.CASTANHO_MEDIO,
            )
            eixo.set_xticks([])
            eixo.set_yticks([])
            figura.tight_layout()
            canvas.draw_idle()
            return

        posicoes = list(range(len(grafico.etiquetas)))
        cores = (_COR_BARRA_1, _COR_BARRA_2)

        if len(grafico.series) <= 1:
            valores = [
                float(v) for v in (grafico.series[0].valores if grafico.series else [])
            ]
            eixo.bar(posicoes, valores, color=_COR_BARRA_1)
        else:
            largura = 0.8 / len(grafico.series)
            for indice, serie in enumerate(grafico.series):
                deslocamento = (indice - (len(grafico.series) - 1) / 2) * largura
                valores = [float(v) for v in serie.valores]
                eixo.bar(
                    [p + deslocamento for p in posicoes],
                    valores,
                    width=largura,
                    label=serie.nome,
                    color=cores[indice % len(cores)],
                )
            eixo.legend()

        eixo.set_xticks(posicoes)
        eixo.set_xticklabels(grafico.etiquetas, rotation=30, ha="right")
        eixo.set_ylabel(grafico.unidade)

        figura.tight_layout()
        canvas.draw_idle()

    def _desenhar_pizza(self, canvas, grafico) -> None:
        """Desenha um GraficoPizza (distribuição de custos) num canvas.

        Uma fatia por categoria, com percentagem dentro da fatia e legenda
        "<nome> — <valor>". Sem fatias -> texto centrado "Sem dados".
        """
        figura = canvas.figure
        figura.clear()
        eixo = figura.add_subplot(111)

        if not grafico.fatias:
            eixo.set_title(grafico.titulo, color=tema.CASTANHO_ESCURO)
            eixo.text(
                0.5, 0.5, "Sem dados",
                ha="center", va="center", transform=eixo.transAxes,
                color=tema.CASTANHO_MEDIO,
            )
            eixo.set_xticks([])
            eixo.set_yticks([])
            figura.tight_layout()
            canvas.draw_idle()
            return

        valores = [float(f.euros) for f in grafico.fatias]
        cores = [
            _CORES_PIZZA[i % len(_CORES_PIZZA)] for i in range(len(grafico.fatias))
        ]
        legendas = [
            f"{f.nome} — {format_currency(f.euros)}" for f in grafico.fatias
        ]

        fatias, _textos, _autotextos = eixo.pie(
            valores, autopct="%1.1f%%", colors=cores
        )
        eixo.set_title(
            f"Distribuição de custos — Total de venda: "
            f"{format_currency(grafico.total_venda)}",
            color=tema.CASTANHO_ESCURO,
        )
        eixo.legend(fatias, legendas, loc="center left", bbox_to_anchor=(1.0, 0.5))
        eixo.axis("equal")

        figura.tight_layout()
        canvas.draw_idle()

    def _titulo_seccao(self, texto: str) -> QLabel:
        label = QLabel(texto)
        label.setStyleSheet(
            f"font-weight: bold; color: {tema.CASTANHO_ESCURO}; padding-top: 4px;"
        )
        return label
