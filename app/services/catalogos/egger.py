"""Adaptador EGGER — o primeiro, porque é o que mais se gasta.

O EGGER chega por dois caminhos, e nenhum deles é o EGGER: quem factura é a
**Balbino & Faustino** (separador ``Stock_B&F_Egger``, 185 decorativos em 8 e
19 mm) ou a **WoodSide** (``Stock_WoodSide_Egger``, 209 decorativos em dez
espessuras, dos 8 aos 38 mm). São tabelas diferentes, com preços diferentes
para a mesma referência, e é por isso que ``fornecedor`` e ``fabricante`` são
campos separados: o fornecedor é quem vende, o fabricante é o EGGER.

Depois do unpivot das espessuras, os dois separadores dão **2 460 artigos** —
370 da B&F e 2 090 da WoodSide — todos com preço em €/m².

O que este adaptador decide:

* **A chave natural é ``referência|ST|substrato|espessura``.** O ST tem de
  entrar: o ``W908`` existe em ``SM`` e em ``ST7``, com o mesmo preço mas
  acabamentos diferentes, e são duas linhas na tabela do fornecedor. Sem o ST,
  a segunda apagava a primeira na reimportação.
* **O substrato sai do «Tipo Produto».** Hoje as duas folhas só têm Eurodekor
  revestido em aglomerado de partículas, e as duas escrevem-no de maneira
  diferente («E1E05» numa, «El E05» na outra — o OCR do PDF). Classificar por
  palavras em vez de comparar o texto todo é o que faz as duas assentarem no
  mesmo ``PB STD``. Um tipo de produto que não se reconheça **não** é
  adivinhado: fica sem substrato e sai um aviso.
* **A data e o código da tabela saem das notas do separador**, não do nome do
  ficheiro nem de uma constante que envelhece aqui dentro.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.services.catalogos import excel_placas
from app.services.catalogos.base import (
    ArtigoCatalogo,
    TabelaCatalogo,
    chave_natural,
    hash_conteudo,
    normalizar,
    primeira_data,
    primeira_referencia_tabela,
    texto,
)

FABRICANTE = "EGGER"
#: Os preços do Eurodekor são por metro quadrado de placa.
UNIDADE = "M2"
#: Quantos avisos linha a linha se mostram antes de se resumir o resto.
MAX_AVISOS_LINHAS = 20


@dataclass(frozen=True, slots=True)
class FolhaEgger:
    """Um separador de EGGER e quem o factura."""

    folha: str
    fornecedor: str
    nome: str


#: Os separadores que este adaptador lê. Acrescentar um fornecedor de EGGER é
#: acrescentar uma linha aqui — o resto do módulo não muda.
FOLHAS: tuple[FolhaEgger, ...] = (
    FolhaEgger(
        folha="Stock_B&F_Egger",
        fornecedor="Balbino & Faustino",
        nome="EGGER Balbino & Faustino",
    ),
    FolhaEgger(
        folha="Stock_WoodSide_Egger",
        fornecedor="WoodSide",
        nome="EGGER WoodSide",
    ),
)


def _substrato(tipo_produto: str | None) -> str | None:
    """O núcleo da placa, a partir do texto do «Tipo Produto».

    Devolve ``None`` quando não reconhece — quem chama transforma isso num
    aviso. Adivinhar um substrato errado é pior do que não ter nenhum: é dele
    que depende comparar o 19 mm de um fornecedor com o de outro.
    """
    if tipo_produto is None:
        return None
    norm = normalizar(tipo_produto)
    hidrofugo = any(
        marca in norm for marca in ("hidrofug", "hydro", "humidade", " p3", "p5")
    )

    if "compacto" in norm or "compact" in norm:
        return "COMPACTO"
    if "mdf" in norm or "fibras" in norm:
        return "MDF HID" if hidrofugo else "MDF STD"
    if "particula" in norm or "aglomerado" in norm or "eurodekor" in norm:
        return "PB HID" if hidrofugo else "PB STD"
    return None


def _descricao(
    referencia: str,
    st: str | None,
    nome_design: str | None,
    espessura: str,
    tipo_produto: str | None,
) -> str:
    """A frase que a Pesquisa IA vai indexar na Fase 3.

    Leva de propósito tudo o que alguém pode escrever na caixa de pesquisa: a
    marca, a referência, o acabamento, o nome do decorativo e a espessura.
    """
    partes = [" ".join(p for p in (FABRICANTE, referencia, st) if p)]
    if nome_design:
        partes.append(nome_design)
    partes.append(espessura.replace("mm", " mm"))
    if tipo_produto:
        partes.append(tipo_produto)
    return " · ".join(partes)


def _familia(tipo_produto: str | None) -> str | None:
    """A linha de produto («Eurodekor»), quando o texto a diz no início."""
    if not tipo_produto:
        return None
    primeira = tipo_produto.split()[0].strip()
    return primeira if primeira.lower() in {"eurodekor", "eurolight", "eurospan"} else None


def _grupo(bruto: object) -> str | None:
    """O grupo de preço, «Grupo 7». Vem como número inteiro do Excel.

    O ``.0`` que o Excel às vezes cola atrás sai por corte explícito e não por
    ``rstrip``: um ``rstrip('.0')`` transformava o Grupo 10 em Grupo 1.
    """
    valor = texto(bruto)
    if valor is None:
        return None
    if normalizar(valor).startswith("grupo"):
        return valor
    if valor.endswith(".0"):
        valor = valor[:-2]
    return f"Grupo {valor}"


def ler_folha(caminho: Path | str, folha: FolhaEgger) -> TabelaCatalogo:
    """Lê um separador de EGGER e devolve a tabela já desdobrada."""
    lida = excel_placas.ler_folha(caminho, folha.folha)
    avisos: list[str] = []

    col_referencia = lida.exigir_coluna("referencia", "refer")
    col_st = lida.coluna("st", "acabamento")
    col_design = lida.coluna("nome design", "design", "decorativo")
    col_grupo = lida.coluna("grupo")
    col_tipo = lida.coluna("tipo produto", "tipo")
    col_fornecedor = lida.coluna("fornecedor")
    col_observacoes = lida.coluna("observacoes", "notas")

    if col_st is None:
        avisos.append(
            "não há coluna ST/acabamento: referências com vários acabamentos "
            "vão colidir na chave natural"
        )

    artigos: list[ArtigoCatalogo] = []
    #: Avisos linha a linha, arrumados à parte para não afogarem os outros:
    #: uma coluna que muda de forma produz um por artigo, e são milhares.
    avisos_linhas: list[str] = []
    tipos_desconhecidos: set[str] = set()
    fornecedores_estranhos: set[str] = set()
    sem_espessura = 0

    for linha in lida.linhas:
        referencia = texto(excel_placas.valor(linha, col_referencia))
        if referencia is None:
            continue

        st = texto(excel_placas.valor(linha, col_st))
        nome_design = texto(excel_placas.valor(linha, col_design))
        tipo_produto = texto(excel_placas.valor(linha, col_tipo))
        observacoes = texto(excel_placas.valor(linha, col_observacoes))
        grupo = _grupo(excel_placas.valor(linha, col_grupo))

        fornecedor_linha = texto(excel_placas.valor(linha, col_fornecedor))
        if fornecedor_linha and normalizar(fornecedor_linha) != normalizar(
            folha.fornecedor
        ):
            fornecedores_estranhos.add(fornecedor_linha)

        substrato = _substrato(tipo_produto)
        if substrato is None and tipo_produto is not None:
            tipos_desconhecidos.add(tipo_produto)

        desdobrada = excel_placas.desdobrar(lida, linha)
        if not desdobrada:
            sem_espessura += 1
            continue

        for medida in desdobrada:
            if medida.aviso:
                avisos_linhas.append(f"{referencia} {st or ''}: {medida.aviso}".strip())
            artigos.append(
                ArtigoCatalogo(
                    chave_natural=chave_natural(
                        referencia, st, substrato, medida.etiqueta
                    ),
                    referencia=referencia,
                    descricao=_descricao(
                        referencia, st, nome_design, medida.etiqueta, tipo_produto
                    ),
                    unidade=UNIDADE,
                    nome_design=nome_design,
                    familia=_familia(tipo_produto),
                    seccao=tipo_produto,
                    grupo=grupo,
                    fabricante=FABRICANTE,
                    substrato=substrato,
                    espessura_mm=medida.espessura_mm,
                    acabamento=st,
                    preco=medida.preco,
                    # Proveniência: de que separador e de que texto de origem
                    # veio a linha, para uma auditoria não ter de adivinhar.
                    atributos={
                        "folha": folha.folha,
                        "st": st,
                        "tipo_produto": tipo_produto,
                        "espessura": medida.etiqueta,
                    },
                    observacoes=observacoes,
                )
            )

    if not artigos:
        raise excel_placas.FormatoInesperado(
            f"{folha.folha}: {len(lida.linhas)} linhas lidas e nenhum artigo. "
            "O cabeçalho das espessuras deve ter mudado."
        )

    if tipos_desconhecidos:
        avisos.append(
            "tipo de produto sem substrato conhecido (artigos ficam sem "
            f"substrato): {', '.join(sorted(tipos_desconhecidos))}"
        )
    if fornecedores_estranhos:
        avisos.append(
            f"a coluna Fornecedor diz {', '.join(sorted(fornecedores_estranhos))} "
            f"mas este separador é do {folha.fornecedor}"
        )
    if sem_espessura:
        avisos.append(f"{sem_espessura} linhas sem espessura nenhuma disponível")
    if avisos_linhas:
        avisos.extend(avisos_linhas[:MAX_AVISOS_LINHAS])
        se_faltam = len(avisos_linhas) - MAX_AVISOS_LINHAS
        if se_faltam > 0:
            avisos.append(f"(e mais {se_faltam} avisos do mesmo tipo)")

    data_tabela = primeira_data(lida.notas)
    ano = f" {data_tabela.year}" if data_tabela else ""

    return TabelaCatalogo(
        fornecedor=folha.fornecedor,
        fabricante=FABRICANTE,
        nome=f"{folha.nome}{ano}",
        referencia_tabela=primeira_referencia_tabela(lida.notas),
        data_tabela=data_tabela,
        ficheiro_origem=f"{Path(caminho).name}#{folha.folha}",
        # Hash das linhas de dados e do cabeçalho, não do ficheiro: o mesmo
        # xlsx traz treze separadores de fornecedores diferentes.
        ficheiro_hash=hash_conteudo([lida.cabecalho, *lida.linhas]),
        moeda="EUR",
        unidade_preco=UNIDADE,
        observacoes="\n".join(lida.notas) or None,
        artigos=tuple(artigos),
        avisos=tuple(avisos),
    )


def ler_tabelas(
    caminho: Path | str, folhas: Sequence[FolhaEgger] | None = None
) -> list[TabelaCatalogo]:
    """As tabelas de EGGER de um ficheiro — uma por separador de ``FOLHAS``."""
    return [ler_folha(caminho, folha) for folha in (folhas or FOLHAS)]
