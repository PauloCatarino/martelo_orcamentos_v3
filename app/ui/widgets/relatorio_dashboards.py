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

# Nº mínimo de "slots" no eixo X: com poucas categorias as barras não esticam.
_MIN_SLOTS_X = 6

# Abaixo desta percentagem a fatia é minúscula -> não desenha a % (evita
# sobreposição em fatias pequeninas).
_PCT_MIN_PIZZA = 3.0

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


def _formatar_pct_pizza(pct: float) -> str:
    """Esconde as percentagens das fatias pequenas (abaixo de _PCT_MIN_PIZZA)."""
    return f"{pct:.1f}%" if pct >= _PCT_MIN_PIZZA else ""


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
            # layout="constrained" recalcula o espaçamento ao redimensionar (as
            # etiquetas do eixo X deixam de ficar cortadas); a pizza leva mais
            # altura para a legenda por baixo.
            altura = 4.2 if chave == "distribuicao" else 3.0
            canvas = FigureCanvas(Figure(figsize=(6, altura), layout="constrained"))
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
            canvas.draw_idle()
            return

        posicoes = list(range(len(grafico.etiquetas)))
        cores = (_COR_BARRA_1, _COR_BARRA_2)

        if len(grafico.series) <= 1:
            valores = [
                float(v) for v in (grafico.series[0].valores if grafico.series else [])
            ]
            eixo.bar(posicoes, valores, width=0.6, color=_COR_BARRA_1)
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
        eixo.set_xticklabels(
            grafico.etiquetas, rotation=30, ha="right", rotation_mode="anchor"
        )
        # Reserva um nº mínimo de slots para as barras não esticarem com poucas
        # categorias.
        eixo.set_xlim(-0.6, max(len(grafico.etiquetas), _MIN_SLOTS_X) - 0.4)
        eixo.set_ylabel(grafico.unidade)

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
            valores, autopct=_formatar_pct_pizza, colors=cores, pctdistance=0.8
        )
        eixo.set_title(
            f"Distribuição de custos — Total de venda: "
            f"{format_currency(grafico.total_venda)}",
            color=tema.CASTANHO_ESCURO,
        )
        # Legenda por baixo: funciona melhor com constrained e deixa a pizza maior.
        eixo.legend(
            fatias, legendas, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=3
        )
        eixo.axis("equal")

        canvas.draw_idle()

    def _titulo_seccao(self, texto: str) -> QLabel:
        label = QLabel(texto)
        label.setStyleSheet(
            f"font-weight: bold; color: {tema.CASTANHO_ESCURO}; padding-top: 4px;"
        )
        return label
