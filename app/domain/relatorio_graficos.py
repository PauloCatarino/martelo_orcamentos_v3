"""Modelos de dados (puros) para os gráficos de barras dos relatórios (fase 8W.3a).

Sem Qt nem matplotlib aqui — apenas transforma as dataclasses de consumo já
calculadas (:mod:`app.domain.consumos`) em modelos simples de gráfico que o
widget dos dashboards desenha. Mantido puro para ser testável sem GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

_ZERO = Decimal("0")

# Comprimento máximo da descrição na etiqueta. As barras são deitadas, por isso
# a etiqueta vai em duas linhas — referência em cima, descrição em baixo — e a
# descrição é cortada aqui para o eixo não empurrar o gráfico todo para a
# direita.
_MAX_ETIQUETA = 30


@dataclass(frozen=True)
class SerieBarras:
    """Uma série de dados (com nome) de um gráfico de barras."""

    nome: str
    valores: list


@dataclass(frozen=True)
class GraficoBarras:
    """Modelo de um gráfico de barras: título, etiquetas X, séries e unidade Y."""

    titulo: str
    etiquetas: list
    series: list
    unidade: str


@dataclass(frozen=True)
class FatiaPizza:
    """Uma fatia (categoria) do gráfico de pizza da distribuição de custos."""

    nome: str
    euros: Decimal
    pct: Decimal


@dataclass(frozen=True)
class GraficoPizza:
    """Modelo de um gráfico de pizza: título, fatias e total de venda."""

    titulo: str
    fatias: list
    total_venda: Decimal


def _truncar(texto: str | None) -> str:
    """Corta uma descrição para um comprimento de etiqueta legível."""
    limpo = (texto or "").strip()
    if len(limpo) <= _MAX_ETIQUETA:
        return limpo
    return limpo[: _MAX_ETIQUETA - 1] + "…"


def _etiqueta_ref(ref, descricao) -> str:
    """Etiqueta = referência EM CIMA e descrição EM BAIXO, em duas linhas.

    Só com a referência (PLC0033, ORL0003, FER0015) ninguém sabe de que
    material se trata — e há referências repetidas na mesma tabela (a mesma
    orla em duas espessuras), que ficavam com duas barras impossíveis de
    distinguir. A descrição por baixo resolve as duas coisas.

    Quando falta uma das duas partes, a etiqueta é só a outra.
    """
    ref_limpa = (ref or "").strip()
    descricao_limpa = _truncar(descricao)
    if ref_limpa and descricao_limpa:
        return f"{ref_limpa}\n{descricao_limpa}"
    return ref_limpa or descricao_limpa


def dados_placas(placas) -> GraficoBarras:
    """Placas: placas inteiras vs. custo no orçamento, em €.

    As duas séries são as duas colunas da tabela do resumo de placas:

    - **C.Placa Usad** — o que custam as placas INTEIRAS que é preciso comprar;
    - **Custo no Orç.** — o que esta placa leva ao orçamento.

    Até aqui a 1.ª série era o custo teórico (C.MP Tot) e, sem Não-Stock, esse
    é exatamente igual ao custo no orçamento: o gráfico desenhava duas barras
    do mesmo comprimento e não dizia nada. Assim mostra a diferença que
    interessa — quanto é que ficam a mais as placas inteiras.
    """
    etiquetas = [_etiqueta_ref(p.ref_le, p.descricao_no_orcamento) for p in placas]
    series = (
        [
            SerieBarras(
                "Placas inteiras (C.Placa Usad)",
                [p.custo_placa_inteira for p in placas],
            ),
            SerieBarras(
                "No orçamento (Custo no Orç.)",
                [p.custo_no_orcamento for p in placas],
            ),
        ]
        if placas
        else []
    )
    return GraficoBarras(
        titulo="Placas — custo",
        etiquetas=etiquetas,
        series=series,
        unidade="€",
    )


def dados_orlas(orlas) -> GraficoBarras:
    """Orlas: uma série de metros lineares, em ml."""
    etiquetas = [_etiqueta_ref(o.ref_orla, o.descricao) for o in orlas]
    series = [SerieBarras("ML", [o.ml_total for o in orlas])] if orlas else []
    return GraficoBarras(
        titulo="Orlas — metros lineares",
        etiquetas=etiquetas,
        series=series,
        unidade="ml",
    )


def dados_ferragens(ferragens) -> GraficoBarras:
    """Ferragens: uma série de custo total, em €."""
    etiquetas = [
        _etiqueta_ref(f.ref_le, f.descricao_no_orcamento) for f in ferragens
    ]
    series = (
        [SerieBarras("Custo", [f.custo_total for f in ferragens])]
        if ferragens
        else []
    )
    return GraficoBarras(
        titulo="Ferragens — custo",
        etiquetas=etiquetas,
        series=series,
        unidade="€",
    )


def dados_maquinas(maquinas) -> GraficoBarras:
    """Máquinas / MO: uma série de custo, em €; só centros com custo_total > 0."""
    com_custo = [m for m in maquinas if m.custo_total > _ZERO]
    etiquetas = [m.centro for m in com_custo]
    series = (
        [SerieBarras("Custo", [m.custo_total for m in com_custo])]
        if com_custo
        else []
    )
    return GraficoBarras(
        titulo="Máquinas / MO — custo",
        etiquetas=etiquetas,
        series=series,
        unidade="€",
    )


#: Os nomes das categorias, como saem de ``consumos.distribuicao_custos``.
#: Um teste garante que continuam a bater certo -- se lá mudarem e aqui não, a
#: pizza por blocos passava a somar zero em silêncio.
CATEGORIA_PLACAS = "Placas"
CATEGORIA_ORLAS = "Orlas"
CATEGORIA_FERRAGENS = "Ferragens"
CATEGORIA_MAQUINAS = "Máquinas / MO"
CATEGORIA_ACABAMENTOS = "Acabamentos"
CATEGORIA_MARGENS = "Margens"

#: As três que o PHC/Martelo trata como um único bloco de matéria-prima no
#: cálculo do preço (``BlocosCusto.bloco_mp``).
CATEGORIAS_MATERIAL = (CATEGORIA_PLACAS, CATEGORIA_ORLAS, CATEGORIA_FERRAGENS)

#: Como se chama esse bloco na pizza dos blocos.
NOME_MATERIAL = "Material (placas + orlas + ferragens)"


def dados_distribuicao(distribuicao) -> GraficoPizza:
    """Distribuição de custos: uma fatia por categoria com euros > 0.

    Ignora categorias a 0 ou negativas (ex.: margem negativa não desenha fatia),
    mantém a ordem das categorias e leva o total de venda para o título.
    """
    fatias = [
        FatiaPizza(c.nome, c.euros, c.pct)
        for c in distribuicao.categorias
        if c.euros > _ZERO
    ]
    return GraficoPizza(
        titulo="Distribuição de custos",
        fatias=fatias,
        total_venda=distribuicao.total_venda,
    )


def dados_distribuicao_blocos(distribuicao) -> GraficoPizza:
    """A mesma venda, vista pelos blocos com que o preço é calculado.

    Material (placas + orlas + ferragens), máquinas/mão de obra, acabamentos e
    margem. Responde a uma pergunta diferente da outra pizza: não "que material
    é que pesa mais", mas "quanto disto é material, quanto é trabalho e quanto
    é margem".

    Os acabamentos são um bloco de custo próprio no cálculo do preço, por isso
    têm fatia própria — mas na maioria dos orçamentos estão a zero e, como
    qualquer categoria a zero, não desenham fatia nenhuma.
    """
    por_nome = {c.nome: c for c in distribuicao.categorias}

    material = sum(
        (por_nome[nome].euros for nome in CATEGORIAS_MATERIAL if nome in por_nome),
        _ZERO,
    )
    total = distribuicao.total_venda

    def pct(euros):
        return (euros / total * Decimal("100")) if total > _ZERO else _ZERO

    fatias = [FatiaPizza(NOME_MATERIAL, material, pct(material))]
    for nome in (CATEGORIA_MAQUINAS, CATEGORIA_ACABAMENTOS, CATEGORIA_MARGENS):
        categoria = por_nome.get(nome)
        if categoria is not None:
            fatias.append(FatiaPizza(nome, categoria.euros, categoria.pct))

    return GraficoPizza(
        titulo="Material, mão de obra e margem",
        fatias=[f for f in fatias if f.euros > _ZERO],
        total_venda=total,
    )
