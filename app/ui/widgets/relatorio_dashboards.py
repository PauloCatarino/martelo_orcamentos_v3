"""Dashboards (gráficos matplotlib embebidos) dos relatórios.

Cinco cartões numa área de scroll: placas, orlas, ferragens e máquinas/MO em
barras deitadas, e no fim as duas leituras da distribuição de custos lado a
lado — a de sempre (uma fatia por categoria) e a por blocos (material, mão de
obra, acabamentos, margem).

Cada cartão tem um cabeçalho com o total e a contagem, para o número que
interessa não ter de ser somado de cabeça.

O matplotlib é opcional: quando não está instalado o widget mostra um aviso em
vez dos gráficos, para o resto da página de relatórios continuar a funcionar. A
modelação (pura) dos dados está em :mod:`app.domain.relatorio_graficos` e o
desenho em :mod:`app.services.dashboard_desenho`, partilhado com o PDF.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.domain import relatorio_graficos
from app.ui import tema
from app.utils.formatters import format_currency

#: Porque e' que os graficos nao abriram. Guardado para o ecra' poder dizer a
#: verdade: durante meses a pagina dizia "Instale matplotlib" quando o
#: matplotlib estava instalado -- o que falhava era o `dateutil` a ser lido
#: depois do shiboken (ver deploy/rthook_dateutil.py). Uma mensagem errada
#: manda a pessoa fazer o que nao serve de nada.
MOTIVO_SEM_GRAFICOS: str | None = None

try:  # matplotlib é opcional (ver docstring do módulo).
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
except ImportError as erro:
    FigureCanvas = Figure = None
    MOTIVO_SEM_GRAFICOS = f"O matplotlib não está instalado ({erro})."
except Exception as erro:  # noqa: BLE001
    FigureCanvas = Figure = None
    MOTIVO_SEM_GRAFICOS = (
        f"O matplotlib está instalado mas não arrancou: "
        f"{type(erro).__name__}: {erro}"
    )

if FigureCanvas is not None:
    from app.services import dashboard_desenho

#: Quantos pixéis vale uma polegada de figura, ao dar altura ao canvas.
_PPP = 96

#: Altura fixa dos dois canvases das pizzas (em polegadas).
ALTURA_PIZZA = 4.6

#: As quatro áreas de barras: chave interna -> (título do cartão, unidade).
_SECCOES_BARRAS = (
    ("placas", "Placas"),
    ("orlas", "Orlas"),
    ("ferragens", "Ferragens"),
    ("maquinas", "Máquinas / MO"),
)


def _mensagem_sem_graficos() -> str:
    """O que dizer quando nao ha' graficos -- a razao verdadeira."""
    if MOTIVO_SEM_GRAFICOS is None:
        return "Instale matplotlib para ver os gráficos."
    return (
        "Não foi possível desenhar os gráficos.\n\n"
        f"{MOTIVO_SEM_GRAFICOS}\n\n"
        "Use 'Reportar problema' para nos enviar esta mensagem."
    )


def _contagem(grafico, singular: str, plural: str) -> str:
    quantas = len(grafico.etiquetas)
    return f"{quantas} {singular if quantas == 1 else plural}"


def _total_barras(grafico) -> str:
    """O total do gráfico: da última série, que é a que conta.

    Nas placas a 1.ª série é o custo teórico e a 2.ª o que está no orçamento —
    é o segundo que interessa somar.
    """
    if not grafico.series:
        return ""
    valores = [float(v) for v in grafico.series[-1].valores]
    total = sum(valores)
    if grafico.unidade == "€":
        return format_currency(total)
    return f"{total:,.2f}".replace(",", " ").replace(".", ",") + f" {grafico.unidade}"


class CartaoGrafico(QFrame):
    """Um gráfico com cabeçalho: título, contagem e total."""

    def __init__(self, titulo: str, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("cartaoGrafico")
        self.setStyleSheet(
            f"QFrame#cartaoGrafico {{ background-color: #FFFFFF;"
            f" border: 1px solid {tema.CINZA_CASTANHO}; border-radius: 6px; }}"
        )
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        fora = QVBoxLayout(self)
        fora.setContentsMargins(0, 0, 0, 0)
        fora.setSpacing(0)

        cabecalho = QWidget()
        cabecalho.setStyleSheet(
            f"background-color: {tema.BEGE_AREIA};"
            f" border-bottom: 1px solid {tema.CINZA_CASTANHO};"
            " border-top-left-radius: 6px; border-top-right-radius: 6px;"
        )
        linha = QHBoxLayout(cabecalho)
        linha.setContentsMargins(12, 7, 12, 7)
        linha.setSpacing(10)

        self.titulo_label = QLabel(titulo)
        self.titulo_label.setStyleSheet(
            f"font-weight: bold; color: {tema.CASTANHO_ESCURO}; background: transparent;"
        )
        self.contagem_label = QLabel("")
        self.contagem_label.setStyleSheet(
            f"color: {tema.CASTANHO_MEDIO}; background: transparent;"
        )
        self.total_label = QLabel("")
        self.total_label.setStyleSheet(
            f"font-weight: bold; color: {tema.CASTANHO_ESCURO}; background: transparent;"
        )
        linha.addWidget(self.titulo_label)
        linha.addWidget(self.contagem_label)
        linha.addStretch(1)
        linha.addWidget(self.total_label)
        fora.addWidget(cabecalho)

        self.corpo = QWidget()
        self.corpo_layout = QVBoxLayout(self.corpo)
        self.corpo_layout.setContentsMargins(8, 8, 8, 8)
        self.corpo_layout.setSpacing(8)
        fora.addWidget(self.corpo)

    def descrever(self, contagem: str, total: str) -> None:
        self.contagem_label.setText(contagem)
        self.total_label.setText(total)


class DashboardsWidget(QWidget):
    """Cartões com os gráficos do orçamento, numa área de scroll."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._canvases: dict[str, object] = {}
        self._cartoes: dict[str, CartaoGrafico] = {}
        self._resumo = None

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        if FigureCanvas is None:
            # Sem matplotlib: mostra o aviso e não cria canvases.
            aviso = QLabel(_mensagem_sem_graficos())
            aviso.setWordWrap(True)
            aviso.setStyleSheet(
                f"color: {tema.CASTANHO_ESCURO}; font-weight: bold; padding: 12px;"
            )
            layout.addWidget(aviso)
            layout.addStretch()
            self.setLayout(layout)
            return

        conteudo = QWidget()
        conteudo_layout = QVBoxLayout(conteudo)
        conteudo_layout.setContentsMargins(0, 0, 0, 0)
        conteudo_layout.setSpacing(12)

        for chave, titulo in _SECCOES_BARRAS:
            cartao = CartaoGrafico(titulo)
            canvas = self._novo_canvas(dashboard_desenho.ALTURA_MINIMA)
            cartao.corpo_layout.addWidget(canvas)
            self._cartoes[chave] = cartao
            self._canvases[chave] = canvas
            conteudo_layout.addWidget(cartao)

        cartao_pizzas = CartaoGrafico("Distribuição de custos")
        lado_a_lado = QHBoxLayout()
        lado_a_lado.setContentsMargins(0, 0, 0, 0)
        lado_a_lado.setSpacing(8)
        for chave in ("distribuicao", "distribuicao_blocos"):
            canvas = self._novo_canvas(ALTURA_PIZZA)
            self._canvases[chave] = canvas
            lado_a_lado.addWidget(canvas, 1)
        cartao_pizzas.corpo_layout.addLayout(lado_a_lado)
        self._cartoes["distribuicao"] = cartao_pizzas
        conteudo_layout.addWidget(cartao_pizzas)

        conteudo_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(conteudo)
        scroll.setStyleSheet(
            f"QScrollArea {{ border: 1px solid {tema.CINZA_CASTANHO};"
            " border-radius: 4px; background-color: #FBF9F6; }"
        )

        layout.addWidget(scroll, stretch=1)
        self.setLayout(layout)

    def _novo_canvas(self, altura_polegadas: float):
        # layout="constrained" recalcula o espaçamento ao redimensionar, para as
        # etiquetas não ficarem cortadas.
        canvas = FigureCanvas(
            Figure(figsize=(7, altura_polegadas), layout="constrained")
        )
        canvas.setMinimumHeight(int(altura_polegadas * _PPP))
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return canvas

    # ----- API pública -----

    def atualizar(self, resumo) -> None:
        """Redesenha os gráficos a partir de um ``ResumoConsumos``."""
        if FigureCanvas is None:
            return
        self._resumo = resumo

        graficos = self.graficos_de_barras(resumo)
        contagens = {
            "placas": ("referência", "referências"),
            "orlas": ("referência", "referências"),
            "ferragens": ("referência", "referências"),
            "maquinas": ("centro", "centros"),
        }
        for chave, grafico in graficos.items():
            singular, plural = contagens[chave]
            self._cartoes[chave].descrever(
                _contagem(grafico, singular, plural), _total_barras(grafico)
            )
            canvas = self._canvases[chave]
            # A altura acompanha o número de linhas: oito ferragens já não
            # ficam espremidas em dois centímetros.
            altura = dashboard_desenho.altura_grafico(grafico)
            canvas.figure.set_size_inches(7, altura)
            canvas.setMinimumHeight(int(altura * _PPP))
            canvas.figure.clear()
            dashboard_desenho.desenhar_barras(canvas.figure, grafico)
            canvas.draw_idle()

        pizza = relatorio_graficos.dados_distribuicao(resumo.distribuicao)
        blocos = relatorio_graficos.dados_distribuicao_blocos(resumo.distribuicao)
        self._cartoes["distribuicao"].descrever(
            "as duas leituras do mesmo total",
            format_currency(resumo.distribuicao.total_venda),
        )
        for chave, grafico in (
            ("distribuicao", pizza),
            ("distribuicao_blocos", blocos),
        ):
            canvas = self._canvases[chave]
            canvas.figure.clear()
            dashboard_desenho.desenhar_pizza(canvas.figure, grafico)
            canvas.draw_idle()

    @staticmethod
    def graficos_de_barras(resumo) -> dict:
        """Os quatro gráficos de barras, pela ordem em que aparecem."""
        return {
            "placas": relatorio_graficos.dados_placas(resumo.placas),
            "orlas": relatorio_graficos.dados_orlas(resumo.orlas),
            "ferragens": relatorio_graficos.dados_ferragens(resumo.ferragens),
            "maquinas": relatorio_graficos.dados_maquinas(resumo.maquinas),
        }
