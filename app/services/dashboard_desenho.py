"""Desenho dos gráficos do dashboard, num sítio só (ecrã e PDF).

O separador Dashboards e o PDF exportado mostram exatamente os mesmos
gráficos — se cada um os desenhasse à sua maneira, mais tarde ou mais cedo
diziam coisas diferentes sobre o mesmo orçamento.

As barras são **deitadas**: as referências (PLC0022, FER0006, "Seccionadora
(Corte)") são compridas e, em pé, ficavam inclinadas a 30° e ilegíveis. Deitadas
leem-se de frente, o valor vai escrito à frente de cada barra, e o gráfico
cresce em altura com o número de linhas em vez de as espremer.

Sem Qt aqui: só matplotlib. Quem chama trata do canvas (ecrã) ou do
``PdfPages`` (ficheiro).
"""

from __future__ import annotations

from app.ui import tema
from app.utils.formatters import format_currency

#: Cores das barras (1.ª e 2.ª série).
COR_BARRA_1 = tema.CASTANHO_MEDIO
COR_BARRA_2 = tema.CASTANHO_ESCURO

#: Altura (em polegadas) de cada linha de um gráfico de barras deitadas.
ALTURA_POR_LINHA = 0.34

#: Altura extra por linha quando há duas séries (placas: teórico + orçamento).
ALTURA_POR_LINHA_DUPLA = 0.52

#: Margem em polegadas para título, eixo e legenda.
ALTURA_FIXA = 1.15

#: Altura mínima: com uma ou duas linhas o gráfico ficava um risco.
ALTURA_MINIMA = 2.0

#: Espaço à direita das barras para o valor escrito não sair do gráfico.
FOLGA_VALOR = 1.16

#: Abaixo desta percentagem a fatia é pequena de mais para lá caber o número.
PCT_MIN_PIZZA = 3.0

#: Paleta da pizza, do mais escuro ao mais claro (a ordem das categorias já é
#: a do custo, por isso o degradé ajuda a ler).
CORES_PIZZA = (
    tema.CASTANHO_ESCURO,
    tema.CASTANHO_MEDIO,
    "#B08D63",
    tema.PLACA_INTEIRA_FUNDO,
    tema.BEGE_AREIA,
    tema.CINZA_CASTANHO,
)

#: Fundos claros onde o texto branco da percentagem não se lê.
_FUNDOS_CLAROS = {tema.PLACA_INTEIRA_FUNDO, tema.BEGE_AREIA, tema.CINZA_CASTANHO}


def altura_grafico(grafico) -> float:
    """Altura (polegadas) de que este gráfico de barras precisa."""
    linhas = max(len(grafico.etiquetas), 1)
    por_linha = (
        ALTURA_POR_LINHA_DUPLA if len(grafico.series) > 1 else ALTURA_POR_LINHA
    )
    return max(ALTURA_MINIMA, ALTURA_FIXA + linhas * por_linha)


def _texto_valor(valor: float, unidade: str) -> str:
    if unidade == "€":
        return format_currency(valor)
    texto = f"{valor:,.2f}".replace(",", " ").replace(".", ",")
    return f"{texto} {unidade}".strip()


def _sem_dados(eixo) -> None:
    eixo.text(
        0.5,
        0.5,
        "Sem dados",
        ha="center",
        va="center",
        transform=eixo.transAxes,
        color=tema.CASTANHO_MEDIO,
    )
    eixo.set_xticks([])
    eixo.set_yticks([])


def desenhar_barras(figura, grafico, *, com_titulo: bool = True) -> None:
    """Desenha um ``GraficoBarras`` deitado numa figura já limpa."""
    eixo = figura.add_subplot(111)
    if com_titulo:
        eixo.set_title(grafico.titulo, color=tema.CASTANHO_ESCURO, fontsize=11)

    if not grafico.etiquetas:
        _sem_dados(eixo)
        return

    # De cima para baixo pela ordem da tabela: o matplotlib desenha o índice 0
    # em baixo, por isso inverte-se o eixo no fim.
    posicoes = list(range(len(grafico.etiquetas)))
    series = grafico.series or []
    cores = (COR_BARRA_1, COR_BARRA_2)
    maximo = max(
        (float(v) for serie in series for v in serie.valores),
        default=0.0,
    )

    if len(series) <= 1:
        valores = [float(v) for v in (series[0].valores if series else [])]
        barras = eixo.barh(posicoes, valores, height=0.62, color=COR_BARRA_1)
        _escrever_valores(eixo, barras, valores, grafico.unidade, maximo)
    else:
        altura = 0.8 / len(series)
        for indice, serie in enumerate(series):
            deslocamento = (indice - (len(series) - 1) / 2) * altura
            valores = [float(v) for v in serie.valores]
            barras = eixo.barh(
                [p + deslocamento for p in posicoes],
                valores,
                height=altura,
                label=serie.nome,
                color=cores[indice % len(cores)],
            )
            _escrever_valores(eixo, barras, valores, grafico.unidade, maximo)
        eixo.legend(loc="lower right", fontsize=8, framealpha=0.9)

    eixo.set_yticks(posicoes)
    eixo.set_yticklabels(grafico.etiquetas, fontsize=9)
    eixo.invert_yaxis()
    eixo.set_xlim(0, (maximo or 1.0) * FOLGA_VALOR)
    eixo.set_xlabel(
        "euros" if grafico.unidade == "€" else grafico.unidade,
        fontsize=9,
        color=tema.CASTANHO_MEDIO,
    )
    eixo.tick_params(axis="x", labelsize=8, colors=tema.CASTANHO_MEDIO)
    eixo.grid(axis="x", color="#E6DFD4", linewidth=0.8)
    eixo.set_axisbelow(True)
    for lado in ("top", "right", "left"):
        eixo.spines[lado].set_visible(False)
    eixo.spines["bottom"].set_color("#E6DFD4")


def _escrever_valores(eixo, barras, valores, unidade, maximo) -> None:
    """O valor à frente de cada barra — poupa a leitura contra o eixo."""
    folga = (maximo or 1.0) * 0.015
    for barra, valor in zip(barras, valores):
        eixo.text(
            barra.get_width() + folga,
            barra.get_y() + barra.get_height() / 2,
            _texto_valor(valor, unidade),
            va="center",
            ha="left",
            fontsize=8,
            color=tema.CASTANHO_ESCURO,
            fontweight="bold",
        )


def _formatar_pct(pct: float) -> str:
    return f"{pct:.1f}%" if pct >= PCT_MIN_PIZZA else ""


def desenhar_pizza(figura, grafico) -> None:
    """Desenha um ``GraficoPizza`` numa figura já limpa, com legenda por baixo."""
    eixo = figura.add_subplot(111)
    eixo.set_title(
        f"{grafico.titulo}\nTotal de venda: {format_currency(grafico.total_venda)}",
        color=tema.CASTANHO_ESCURO,
        fontsize=10,
    )

    if not grafico.fatias:
        _sem_dados(eixo)
        return

    valores = [float(f.euros) for f in grafico.fatias]
    cores = [CORES_PIZZA[i % len(CORES_PIZZA)] for i in range(len(grafico.fatias))]
    fatias, _textos, percentagens = eixo.pie(
        valores,
        autopct=_formatar_pct,
        colors=cores,
        pctdistance=0.72,
        wedgeprops={"edgecolor": "#FFFFFF", "linewidth": 1.5},
        textprops={"fontsize": 9, "fontweight": "bold"},
    )
    for texto, cor in zip(percentagens, cores):
        texto.set_color(tema.TEXTO_NORMAL if cor in _FUNDOS_CLAROS else "#FFFFFF")

    eixo.legend(
        fatias,
        [f"{f.nome} — {format_currency(f.euros)}" for f in grafico.fatias],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=1,
        fontsize=8,
        frameon=False,
    )
    eixo.axis("equal")
