"""Adaptador das ferragens e acessórios — quatro fornecedores, um só módulo.

Depois das placas vêm os separadores de quem vende o resto: **Emuca** (3 340
artigos), **Casa Trend** (5 000), **FIWARE** (806) e o **BLUM** da Somapil
(720). São 9 866 linhas, quase todas com preço.

Aqui não há unpivot: uma linha é um artigo e um preço. O que muda de
fornecedor para fornecedor é só **como se chamam as colunas** e **o que é
preciso para identificar um artigo** — e isso escreve-se como dados, no
``FOLHAS`` lá em baixo, e não como código. Um fornecedor novo de ferragens é
uma entrada nessa lista.

As três decisões que os dados obrigaram a tomar:

* **A referência nem sempre chega.** No BLUM a mesma referência aparece até
  dez vezes: o PDF lista-a como preço unitário e como preço de conjunto, em
  secções diferentes e com designações diferentes, e os preços são mesmo
  diferentes. Por isso cada folha declara em ``chave`` que outras colunas
  entram na chave natural. Sem isso perdiam-se 103 linhas de preços.
* **Casa Trend repete de propósito.** O mesmo artigo aparece listado em várias
  famílias do catálogo, com o mesmo preço — a própria folha o diz. Aí as
  linhas **juntam-se** numa só, com as famílias todas guardadas, em vez de
  darem erro.
* **Os códigos de barras e as referências do fabricante viram aliases.** A
  Emuca traz o EAN, o BLUM traz o código interno. Sem isso a pesquisa falha
  sempre que alguém procura pelo código que tem à frente em vez daquele que
  ficou no catálogo.
"""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path

from app.services.catalogos import excel
from app.services.catalogos.base import (
    ALIAS_EAN,
    ALIAS_FABRICANTE,
    ArtigoCatalogo,
    FormatoInesperado,
    TabelaCatalogo,
    chave_natural,
    hash_conteudo,
    normalizar,
    numero,
    primeira_data,
    primeira_referencia_tabela,
    texto,
)

MAX_AVISOS_LINHAS = 20

#: Unidades que se sabem traduzir para o vocabulário da base. O que não estiver
#: aqui passa tal e qual — é melhor guardar o que o fornecedor escreveu do que
#: inventar uma unidade.
UNIDADES = {
    "un": "UN", "und": "UN", "uni": "UN", "unidade": "UN", "pc": "UN", "pcs": "UN",
    "mt": "ML", "m": "ML", "ml": "ML", "metro": "ML",
    "m2": "M2", "m²": "M2",
}
#: Unidades que não são unidades. O «%» aparece em doze linhas da FIWARE, em
#: artigos com preço e descrição normais: é gralha da tabela, não um artigo
#: cobrado à percentagem. Fica UN e sai um aviso com as referências.
UNIDADES_SUSPEITAS = {"%", "0", "-"}


@dataclass(frozen=True)
class FolhaFerragens:
    """Um separador de ferragens e como se lê.

    Cada campo é uma lista de nomes possíveis para a coluna, procurados por
    igualdade antes de inclusão. Uma lista vazia quer dizer «este separador não
    tem essa coluna» — e é preciso dizê-lo, senão uma procura por ``un`` iria
    encontrar o ``Componentes do conjunto`` do BLUM.
    """

    folha: str
    fornecedor: str
    nome: str
    fabricante: str | None = None
    referencia: tuple[str, ...] = ("referencia artigo", "referencia")
    descricao: tuple[str, ...] = ("descricao pt", "descricao")
    preco: tuple[str, ...] = ("preco tabela",)
    unidade: tuple[str, ...] = ()
    familia: tuple[str, ...] = ()
    seccao: tuple[str, ...] = ()
    catalogo: tuple[str, ...] = ()
    pagina: tuple[str, ...] = ()
    grupo: tuple[str, ...] = ()
    observacoes: tuple[str, ...] = ()
    #: Colunas que entram na chave natural, além da referência.
    chave: tuple[str, ...] = ()
    #: ``(tipo do alias, nome da coluna)`` — ver ``FornArtigoAlias``.
    aliases: tuple[tuple[str, str], ...] = ()
    #: Colunas guardadas em ``atributos`` tal como vieram.
    atributos: tuple[str, ...] = ()
    #: Quando a mesma chave aparece mais do que uma vez de propósito.
    juntar_repetidas: bool = False
    unidade_omissao: str = "UN"


FOLHAS: tuple[FolhaFerragens, ...] = (
    FolhaFerragens(
        folha="Emuca_2026",
        fornecedor="Emuca",
        fabricante="Emuca",
        nome="Emuca",
        referencia=("referencia",),
        descricao=("descricao pt", "designacao es"),
        preco=("preco tabela",),
        unidade=("und",),
        aliases=((ALIAS_EAN, "codigo barras"),),
        atributos=("box", "designacao es"),
    ),
    FolhaFerragens(
        folha="CasaTrend_2026",
        fornecedor="Casa Trend",
        nome="Casa Trend",
        preco=("preco tabela",),
        unidade=("unidade",),
        familia=("familia produto",),
        seccao=("grupo/seccao",),
        catalogo=("cod. catalogo",),
        pagina=("pag.",),
        atributos=("stock", "atributos", "ficheiro origem", "tabela"),
        # A folha avisa que a mesma referência aparece em várias famílias com
        # o mesmo preço. São 37 referências, 15 delas em famílias diferentes.
        juntar_repetidas=True,
    ),
    FolhaFerragens(
        folha="Fiware_2026",
        fornecedor="FIWARE",
        fabricante="FIWARE",
        nome="FIWARE",
        preco=("preco pvp1",),
        unidade=("un",),
        atributos=("tab",),
    ),
    FolhaFerragens(
        folha="Somapil_BLUM",
        fornecedor="Somapil",
        fabricante="BLUM",
        nome="BLUM · Somapil",
        preco=("preco tabela eur sem iva",),
        familia=("familia",),
        seccao=("seccao pdf",),
        # A «Página PDF» do BLUM não é um número de página: é a lista das
        # páginas onde o artigo aparece («5 | 6 | 12 | …», até 70 caracteres) e
        # não cabe na coluna. Fica só nos atributos.
        grupo=("base do preco",),
        observacoes=("observacoes",),
        # Cinco partes, e são precisas: ver a docstring do módulo.
        chave=("descricao", "base do preco", "seccao pdf", "designacao blum completa"),
        aliases=((ALIAS_FABRICANTE, "codigo blum"),),
        atributos=(
            "base do preco", "designacao blum completa", "embalagem no pdf",
            "componentes do conjunto", "aplicacao / exemplo no pdf",
            "pagina pdf", "seccao pdf",
        ),
    ),
)


def _unidade(bruto: object, omissao: str) -> tuple[str, bool]:
    """A unidade normalizada e se ela é de fiar."""
    valor = texto(bruto)
    if valor is None:
        return omissao, True
    if valor.strip() in UNIDADES_SUSPEITAS:
        return omissao, False
    return UNIDADES.get(normalizar(valor), valor.strip()[:10]), True


def _separar_aliases(bruto: object) -> list[str]:
    """Os códigos de uma célula de alias, que às vezes traz mais do que um.

    O BLUM escreve ``06303402 | 06303582`` numa célula só. Guardados juntos,
    nenhum dos dois seria encontrado por quem procurasse por um deles — que é
    exatamente o que a tabela de aliases existe para resolver.
    """
    valor = texto(bruto)
    if valor is None:
        return []
    partes = [p.strip() for p in re.split(r"[|;/]", valor)]
    return [p for p in partes if p]


def _descricao(partes: Sequence[str | None], fabricante: str | None) -> str:
    """A frase que a Pesquisa IA vai indexar na Fase 3."""
    limpas = [p for p in partes if p]
    if fabricante and not any(
        normalizar(fabricante) in normalizar(p) for p in limpas
    ):
        limpas.insert(0, fabricante)
    return " · ".join(limpas)


def ler_folha(caminho: Path | str, folha: FolhaFerragens) -> TabelaCatalogo:
    """Lê um separador de ferragens e devolve a tabela."""
    lida = excel.ler_folha(caminho, folha.folha)
    avisos: list[str] = []

    def col(nomes: tuple[str, ...]) -> int | None:
        return lida.coluna(*nomes) if nomes else None

    col_referencia = lida.exigir_coluna(*folha.referencia)
    col_descricao = col(folha.descricao)
    col_preco = col(folha.preco)
    if col_preco is None:
        raise FormatoInesperado(
            f"{folha.folha}: não há coluna de preço "
            f"({' / '.join(folha.preco)}). O cabeçalho tem: "
            f"{', '.join(lida.cabecalho)}"
        )
    col_unidade = col(folha.unidade)
    col_familia = col(folha.familia)
    col_seccao = col(folha.seccao)
    col_catalogo = col(folha.catalogo)
    col_pagina = col(folha.pagina)
    col_grupo = col(folha.grupo)
    col_observacoes = col(folha.observacoes)
    cols_chave = [(nome, lida.coluna(nome)) for nome in folha.chave]
    cols_atributos = [(nome, lida.coluna(nome)) for nome in folha.atributos]

    em_falta = [nome for nome, indice in cols_chave if indice is None]
    if em_falta:
        raise FormatoInesperado(
            f"{folha.folha}: a chave natural precisa de {', '.join(em_falta)}, "
            f"que não está no cabeçalho: {', '.join(lida.cabecalho)}"
        )

    #: chave natural -> artigo, para juntar as repetidas do Casa Trend.
    por_chave: dict[str, ArtigoCatalogo] = {}
    familias_por_chave: dict[str, list[str]] = defaultdict(list)
    unidades_suspeitas: list[str] = []
    repetidas: list[str] = []
    sem_preco = 0

    for linha in lida.linhas:
        referencia = texto(excel.valor(linha, col_referencia))
        if referencia is None:
            continue

        descricao_bruta = texto(excel.valor(linha, col_descricao))
        preco = numero(excel.valor(linha, col_preco))
        if preco is None:
            sem_preco += 1
        familia = texto(excel.valor(linha, col_familia))
        unidade, de_fiar = _unidade(excel.valor(linha, col_unidade), folha.unidade_omissao)
        if not de_fiar:
            unidades_suspeitas.append(referencia)

        partes_chave = [referencia] + [
            texto(excel.valor(linha, indice)) for _, indice in cols_chave
        ]
        chave = chave_natural(*partes_chave)

        atributos = {
            nome: texto(excel.valor(linha, indice))
            for nome, indice in cols_atributos
            if indice is not None
        }
        atributos["folha"] = folha.folha

        aliases = tuple(
            (tipo, parte)
            for tipo, nome_coluna in folha.aliases
            for parte in _separar_aliases(
                excel.valor(linha, lida.coluna(nome_coluna))
            )
        )

        if chave in por_chave:
            if folha.juntar_repetidas:
                if familia:
                    familias_por_chave[chave].append(familia)
                continue
            repetidas.append(chave)
            continue

        if familia:
            familias_por_chave[chave].append(familia)

        por_chave[chave] = ArtigoCatalogo(
            chave_natural=chave,
            referencia=referencia,
            descricao=_descricao(
                [descricao_bruta or referencia], folha.fabricante
            ),
            unidade=unidade,
            familia=familia,
            seccao=texto(excel.valor(linha, col_seccao)),
            catalogo=texto(excel.valor(linha, col_catalogo)),
            pagina=texto(excel.valor(linha, col_pagina)),
            grupo=texto(excel.valor(linha, col_grupo)),
            fabricante=folha.fabricante,
            preco=preco,
            atributos=atributos,
            observacoes=texto(excel.valor(linha, col_observacoes)),
            aliases=aliases,
        )

    if not por_chave:
        raise FormatoInesperado(
            f"{folha.folha}: {len(lida.linhas)} linhas lidas e nenhum artigo."
        )

    # As famílias todas de uma referência que aparece em várias.
    artigos: list[ArtigoCatalogo] = []
    juntas = 0
    for chave, artigo in por_chave.items():
        familias = sorted(set(familias_por_chave.get(chave, [])))
        if len(familias) > 1:
            juntas += 1
            atributos = dict(artigo.atributos or {})
            atributos["familias"] = familias
            artigo = replace(artigo, atributos=atributos)
        artigos.append(artigo)

    if juntas:
        avisos.append(
            f"{juntas} referências aparecem em mais do que uma família do "
            "catálogo, com o mesmo preço; ficaram num artigo só, com as "
            "famílias todas guardadas"
        )
    if repetidas:
        avisos.extend(
            f"chave repetida no separador, segunda ignorada: {c}"
            for c in repetidas[:MAX_AVISOS_LINHAS]
        )
        if len(repetidas) > MAX_AVISOS_LINHAS:
            avisos.append(f"(e mais {len(repetidas) - MAX_AVISOS_LINHAS} repetidas)")
    if unidades_suspeitas:
        avisos.append(
            f"{len(unidades_suspeitas)} linhas com unidade que não é unidade "
            f"(ficaram {folha.unidade_omissao}): "
            + ", ".join(unidades_suspeitas[:10])
        )
    if sem_preco:
        avisos.append(
            f"{sem_preco} artigos sem preço (a tabela lista-os na mesma; "
            "no BLUM quer dizer sob consulta)"
        )

    return TabelaCatalogo(
        fornecedor=folha.fornecedor,
        fabricante=folha.fabricante,
        nome=folha.nome,
        referencia_tabela=primeira_referencia_tabela(lida.notas),
        data_tabela=primeira_data(lida.notas),
        ficheiro_origem=f"{Path(caminho).name}#{folha.folha}",
        ficheiro_hash=hash_conteudo([lida.cabecalho, *lida.linhas]),
        moeda="EUR",
        unidade_preco="UN",
        observacoes="\n".join(lida.notas) or None,
        artigos=tuple(artigos),
        avisos=tuple(avisos),
    )


def ler_tabelas(
    caminho: Path | str, folhas: Sequence[FolhaFerragens] | None = None
) -> list[TabelaCatalogo]:
    """As tabelas de ferragens de um ficheiro — uma por separador de ``FOLHAS``."""
    return [ler_folha(caminho, folha) for folha in (folhas or FOLHAS)]
