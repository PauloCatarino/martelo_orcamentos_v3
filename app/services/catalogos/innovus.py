"""Adaptador INNOVUS (Sonae Arauco) — o segundo, a seguir ao EGGER.

Os preços de Innovus que a casa usa vêm da **Balbino & Faustino**, de dois PDFs
que já foram passados a separador: o ``T-04`` dos brancos (79 linhas) e o
``T-17`` dos decorativos (1 807 linhas). Depois do unpivot das espessuras dão
**8 900 artigos** — mais do triplo do EGGER, porque cada referência aparece
repetida por substrato e há doze substratos.

Estes separadores são mais generosos do que os do EGGER: já trazem o substrato
em coluna própria, a unidade, os formatos, o fabricante e o código da tabela.
O adaptador lê-os das colunas em vez de os adivinhar, e por isso é mais curto
apesar de ler dez vezes mais linhas.

O que este adaptador decide:

* **A chave natural é ``referência|substrato de origem|espessura``.** A
  referência da Innovus já traz o acabamento colado (``B3822 MA``), por isso o
  acabamento não precisa de entrar outra vez. O substrato precisa, e tem de ser
  o **nome de origem** e não o canónico: ``PB STD`` e ``PB STD CARB2`` são duas
  linhas com preços diferentes que o canónico junta no mesmo ``PB STD``. Ver
  ``substratos.py`` para a razão de haver dois níveis.
* **Não há colunas «Esp NNmm»**: aqui a célula de preço vazia é que quer dizer
  que aquela espessura não existe naquele substrato. O ``excel_placas`` já
  trata dos dois casos.
* **A data e o código da tabela saem da coluna «Tabela»** (``T-04 ·
  2026/08/03``), que é por linha e não por separador — e assim uma tabela nova
  traz a data nova sem se mexer em código.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from app.services.catalogos import excel_placas, substratos
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

FABRICANTE = "Innovus"
UNIDADE_OMISSAO = "M2"
MAX_AVISOS_LINHAS = 20


@dataclass(frozen=True, slots=True)
class FolhaInnovus:
    """Um separador de Innovus e quem o factura."""

    folha: str
    fornecedor: str
    nome: str


#: Só os separadores **com preço**. Os três de disponibilidade
#: (``Stock_Somapil_Innovus`` e companhia) têm outra forma — uma matriz de
#: formato × espessura, sem preço nenhum — e um deles não diz a que substrato
#: pertence cada coluna. Ficam de fora até isso estar resolvido na origem.
FOLHAS: tuple[FolhaInnovus, ...] = (
    FolhaInnovus(
        folha="BF_Innovus_Brancos_2026",
        fornecedor="Balbino & Faustino",
        nome="Innovus Brancos E05 · Balbino & Faustino",
    ),
    FolhaInnovus(
        folha="BF_Innovus_Decorativos_2026",
        fornecedor="Balbino & Faustino",
        nome="Innovus Decorativos E05 · Balbino & Faustino",
    ),
)


def _descricao(
    referencia: str,
    nome_design: str | None,
    substrato_origem: str | None,
    substrato_descricao: str | None,
    espessura: str,
) -> str:
    """A frase que a Pesquisa IA vai indexar na Fase 3."""
    partes = [f"{FABRICANTE} {referencia}"]
    if nome_design:
        partes.append(nome_design)
    partes.append(espessura.replace("mm", " mm"))
    if substrato_descricao:
        partes.append(substrato_descricao)
    elif substrato_origem:
        partes.append(substrato_origem)
    return " · ".join(partes)


def ler_folha(caminho: Path | str, folha: FolhaInnovus) -> TabelaCatalogo:
    """Lê um separador de Innovus e devolve a tabela já desdobrada."""
    lida = excel_placas.ler_folha(caminho, folha.folha)
    avisos: list[str] = []
    avisos_linhas: list[str] = []

    col_referencia = lida.exigir_coluna("referencia", "refer")
    col_substrato = lida.exigir_coluna("substrato")
    col_design = lida.coluna("nome design", "design")
    col_ref_base = lida.coluna("ref. base", "ref base")
    col_acabamento = lida.coluna("acabamento")
    col_substrato_desc = lida.coluna("substrato descricao")
    col_principal = lida.coluna("principal")
    col_grupo = lida.coluna("grupo")
    col_unidade = lida.coluna("unidade")
    col_formatos = lida.coluna("formatos")
    col_fornecedor = lida.coluna("fornecedor")
    col_fabricante = lida.coluna("fabricante")
    col_familia = lida.coluna("familia produto")
    col_observacoes = lida.coluna("observacoes")
    col_tabela = lida.coluna("tabela")
    col_ficheiro = lida.coluna("ficheiro origem")

    artigos: list[ArtigoCatalogo] = []
    origens_desconhecidas: set[str] = set()
    fornecedores_estranhos: set[str] = set()
    tabelas_vistas: set[str] = set()
    ficheiros_vistos: set[str] = set()
    sem_espessura = 0

    for linha in lida.linhas:
        referencia = texto(excel_placas.valor(linha, col_referencia))
        if referencia is None:
            continue

        substrato_origem = texto(excel_placas.valor(linha, col_substrato))
        substrato_desc = texto(excel_placas.valor(linha, col_substrato_desc))
        nome_design = texto(excel_placas.valor(linha, col_design))
        acabamento = texto(excel_placas.valor(linha, col_acabamento))
        grupo = texto(excel_placas.valor(linha, col_grupo))
        formatos = texto(excel_placas.valor(linha, col_formatos))
        familia = texto(excel_placas.valor(linha, col_familia))
        observacoes = texto(excel_placas.valor(linha, col_observacoes))
        unidade = texto(excel_placas.valor(linha, col_unidade)) or UNIDADE_OMISSAO
        principal = normalizar(excel_placas.valor(linha, col_principal)) == "sim"

        fornecedor_linha = texto(excel_placas.valor(linha, col_fornecedor))
        if fornecedor_linha and normalizar(fornecedor_linha) != normalizar(
            folha.fornecedor
        ):
            fornecedores_estranhos.add(fornecedor_linha)

        tabela_linha = texto(excel_placas.valor(linha, col_tabela))
        if tabela_linha:
            tabelas_vistas.add(tabela_linha)
        ficheiro_linha = texto(excel_placas.valor(linha, col_ficheiro))
        if ficheiro_linha:
            ficheiros_vistos.add(ficheiro_linha)

        # O canónico é para comparar entre fornecedores; o de origem é o que
        # distingue duas linhas desta tabela — ver substratos.py.
        substrato = substratos.canonico(substrato_desc or substrato_origem)
        if substrato is None and substrato_origem is not None:
            origens_desconhecidas.add(substrato_origem)

        desdobrada = excel_placas.desdobrar(lida, linha)
        if not desdobrada:
            sem_espessura += 1
            continue

        for medida in desdobrada:
            if medida.aviso:
                avisos_linhas.append(f"{referencia}: {medida.aviso}")
            artigos.append(
                ArtigoCatalogo(
                    chave_natural=chave_natural(
                        referencia, substrato_origem, medida.etiqueta
                    ),
                    referencia=referencia,
                    descricao=_descricao(
                        referencia,
                        nome_design,
                        substrato_origem,
                        substrato_desc,
                        medida.etiqueta,
                    ),
                    unidade=unidade,
                    nome_design=nome_design,
                    familia=familia,
                    seccao=substrato_desc,
                    grupo=grupo,
                    fabricante=texto(excel_placas.valor(linha, col_fabricante))
                    or FABRICANTE,
                    substrato=substrato,
                    espessura_mm=medida.espessura_mm,
                    acabamento=acabamento,
                    formatos=formatos,
                    preco=medida.preco,
                    atributos={
                        "folha": folha.folha,
                        "substrato_origem": substrato_origem,
                        "ref_base": texto(excel_placas.valor(linha, col_ref_base)),
                        # «Principal» marca, entre os doze substratos da mesma
                        # referência, o que a tabela considera o normal.
                        "principal": principal,
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

    if origens_desconhecidas:
        avisos.append(
            "substrato sem código canónico (artigos ficam sem substrato, mas "
            "com o nome de origem): " + ", ".join(sorted(origens_desconhecidas))
        )
    if fornecedores_estranhos:
        avisos.append(
            f"a coluna Fornecedor diz {', '.join(sorted(fornecedores_estranhos))} "
            f"mas este separador é do {folha.fornecedor}"
        )
    if len(tabelas_vistas) > 1:
        avisos.append(
            "o separador mistura tabelas diferentes: "
            + ", ".join(sorted(tabelas_vistas))
        )
    if sem_espessura:
        avisos.append(f"{sem_espessura} linhas sem preço em espessura nenhuma")
    if avisos_linhas:
        avisos.extend(avisos_linhas[:MAX_AVISOS_LINHAS])
        se_faltam = len(avisos_linhas) - MAX_AVISOS_LINHAS
        if se_faltam > 0:
            avisos.append(f"(e mais {se_faltam} avisos do mesmo tipo)")

    # A coluna «Tabela» diz «T-04 · 2026/08/03»; as notas do topo repetem-no.
    # Prefere-se a coluna, que é dado, às notas, que são prosa.
    referencia_tabela = None
    data_tabela = None
    if len(tabelas_vistas) == 1:
        (unica,) = tabelas_vistas
        referencia_tabela = primeira_referencia_tabela([unica])
        data_tabela = primeira_data([unica])
    referencia_tabela = referencia_tabela or primeira_referencia_tabela(lida.notas)
    data_tabela = data_tabela or primeira_data(lida.notas)

    origem = f"{Path(caminho).name}#{folha.folha}"
    if len(ficheiros_vistos) == 1:
        (pdf,) = ficheiros_vistos
        origem = f"{origem} ({pdf})"

    return TabelaCatalogo(
        fornecedor=folha.fornecedor,
        fabricante=FABRICANTE,
        nome=folha.nome,
        referencia_tabela=referencia_tabela,
        data_tabela=data_tabela,
        ficheiro_origem=origem,
        ficheiro_hash=hash_conteudo([lida.cabecalho, *lida.linhas]),
        moeda="EUR",
        unidade_preco=UNIDADE_OMISSAO,
        observacoes="\n".join(lida.notas) or None,
        artigos=tuple(artigos),
        avisos=tuple(avisos),
    )


def ler_tabelas(
    caminho: Path | str, folhas: Sequence[FolhaInnovus] | None = None
) -> list[TabelaCatalogo]:
    """As tabelas de Innovus com preço — uma por separador de ``FOLHAS``."""
    return [ler_folha(caminho, folha) for folha in (folhas or FOLHAS)]
