"""Adaptador FINSA — o último, porque é o que menos se gasta.

Da Finsa quase só se compra melamina Linho Cancun, mas o separador
``Stock_B&F_Finsa`` é o maior do ficheiro: 2 873 linhas, quarenta colunas, e
**17 339 preços** depois do unpivot — mais do que o EGGER e a Innovus juntos. É
o que acontece quando cada referência aparece repetida por doze substratos e
cada substrato tem até quinze espessuras.

O que este adaptador decide:

* **A chave natural leva o nome do decorativo**, ao contrário dos outros dois:
  ``referência|design|acabamento|substrato de origem|espessura``. Não é
  cerimónia — a referência ``688B`` com acabamento ``YOKU`` aparece duas vezes
  em cada substrato, uma como ``CARYA WOOD`` (Grupo 3) e outra como ``TIVOLI
  ASH`` (Grupo 2), com preços diferentes. Sem o design na chave, doze pares de
  linhas colidiam e metade dos preços perdia-se. O adaptador **avisa** sempre
  que isto acontece, porque tem todo o ar de ser uma gralha na tabela de
  origem e alguém deve perguntar à Finsa.
* **O substrato de origem entra na chave**, como na Innovus: ``AGL STD`` e
  ``AGL STD EZ`` são preços diferentes que o código canónico junta no mesmo
  ``PB STD``. O ``SUPERPAN`` é núcleo próprio e não um aglomerado — ver
  ``substratos.py``.
* **O grupo é a «Tabela Família»** (``DUO GRUPO 2``) e não a coluna ``Grupo``,
  que só tem o número solto: é a família que diz de que tabela de preços do PDF
  saiu a linha.
"""

from __future__ import annotations

from collections import defaultdict
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

FABRICANTE = "FINSA"
UNIDADE = "M2"
MAX_AVISOS_LINHAS = 20


@dataclass(frozen=True, slots=True)
class FolhaFinsa:
    """Um separador de FINSA e quem o factura."""

    folha: str
    fornecedor: str
    nome: str


FOLHAS: tuple[FolhaFinsa, ...] = (
    FolhaFinsa(
        folha="Stock_B&F_Finsa",
        fornecedor="Balbino & Faustino",
        nome="FINSA Balbino & Faustino",
    ),
)


def _descricao(
    referencia: str,
    nome_design: str | None,
    acabamento: str | None,
    substrato_origem: str | None,
    espessura: str,
) -> str:
    """A frase que a Pesquisa IA vai indexar na Fase 3."""
    partes = [" ".join(p for p in (FABRICANTE, referencia, acabamento) if p)]
    if nome_design:
        partes.append(nome_design)
    partes.append(espessura.replace("mm", " mm"))
    if substrato_origem:
        partes.append(substrato_origem)
    return " · ".join(partes)


def ler_folha(caminho: Path | str, folha: FolhaFinsa) -> TabelaCatalogo:
    """Lê o separador da FINSA e devolve a tabela já desdobrada."""
    lida = excel_placas.ler_folha(caminho, folha.folha)
    avisos: list[str] = []
    avisos_linhas: list[str] = []

    col_referencia = lida.exigir_coluna("referencia", "refer")
    col_substrato = lida.exigir_coluna("tipo/substrato", "substrato", "tipo")
    col_acabamento = lida.coluna("acab.", "acabamento")
    col_design = lida.coluna("nome design", "design")
    col_familia = lida.coluna("familia produto")
    col_tabela_familia = lida.coluna("tabela familia")
    col_grupo = lida.coluna("grupo")
    col_fornecedor = lida.coluna("fornecedor")
    col_observacoes = lida.coluna("observacoes")

    artigos: list[ArtigoCatalogo] = []
    origens_desconhecidas: set[str] = set()
    fornecedores_estranhos: set[str] = set()
    sem_espessura = 0
    #: (referência, acabamento, substrato) -> os designs que lá aparecem. É o
    #: que apanha o caso do 688B YOKU — ver a docstring do módulo.
    designs_por_chave: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    for linha in lida.linhas:
        referencia = texto(excel_placas.valor(linha, col_referencia))
        if referencia is None:
            continue

        substrato_origem = texto(excel_placas.valor(linha, col_substrato))
        acabamento = texto(excel_placas.valor(linha, col_acabamento))
        nome_design = texto(excel_placas.valor(linha, col_design))
        familia = texto(excel_placas.valor(linha, col_familia))
        observacoes = texto(excel_placas.valor(linha, col_observacoes))
        grupo = texto(excel_placas.valor(linha, col_tabela_familia)) or texto(
            excel_placas.valor(linha, col_grupo)
        )

        designs_por_chave[
            (referencia, acabamento or "", substrato_origem or "")
        ].add(nome_design or "")

        fornecedor_linha = texto(excel_placas.valor(linha, col_fornecedor))
        if fornecedor_linha and normalizar(fornecedor_linha) != normalizar(
            folha.fornecedor
        ):
            fornecedores_estranhos.add(fornecedor_linha)

        substrato = substratos.canonico(substrato_origem)
        if substrato is None and substrato_origem is not None:
            origens_desconhecidas.add(substrato_origem)

        desdobrada = excel_placas.desdobrar(lida, linha)
        if not desdobrada:
            sem_espessura += 1
            continue

        for medida in desdobrada:
            if medida.aviso:
                avisos_linhas.append(f"{referencia} {acabamento or ''}: {medida.aviso}".strip())
            artigos.append(
                ArtigoCatalogo(
                    chave_natural=chave_natural(
                        referencia,
                        nome_design,
                        acabamento,
                        substrato_origem,
                        medida.etiqueta,
                    ),
                    referencia=referencia,
                    descricao=_descricao(
                        referencia,
                        nome_design,
                        acabamento,
                        substrato_origem,
                        medida.etiqueta,
                    ),
                    unidade=UNIDADE,
                    nome_design=nome_design,
                    familia=familia,
                    seccao=substrato_origem,
                    grupo=grupo,
                    fabricante=FABRICANTE,
                    substrato=substrato,
                    espessura_mm=medida.espessura_mm,
                    acabamento=acabamento,
                    preco=medida.preco,
                    atributos={
                        "folha": folha.folha,
                        "substrato_origem": substrato_origem,
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

    ambiguas = {
        chave: designs
        for chave, designs in designs_por_chave.items()
        if len(designs) > 1
    }
    if ambiguas:
        exemplos = "; ".join(
            # Uma seta «→» nao existe na cp1252, que e' o que uma consola
            # Windows por omissao usa: o print do aviso rebentava com
            # UnicodeEncodeError e levava a importacao inteira com ele, ANTES
            # de escrever seja o que for. Aqui vale mais o ASCII.
            f"{ref} {acab} {subs} -> {' / '.join(sorted(d for d in designs if d))}"
            for (ref, acab, subs), designs in sorted(ambiguas.items())[:3]
        )
        avisos.append(
            f"{len(ambiguas)} combinações referência+acabamento+substrato com "
            f"mais do que um nome de decorativo (a confirmar com a Finsa; o "
            f"design entra na chave para nenhuma se perder): {exemplos}"
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
    if sem_espessura:
        avisos.append(f"{sem_espessura} linhas sem espessura nenhuma disponível")
    if avisos_linhas:
        avisos.extend(avisos_linhas[:MAX_AVISOS_LINHAS])
        se_faltam = len(avisos_linhas) - MAX_AVISOS_LINHAS
        if se_faltam > 0:
            avisos.append(f"(e mais {se_faltam} avisos do mesmo tipo)")

    return TabelaCatalogo(
        fornecedor=folha.fornecedor,
        fabricante=FABRICANTE,
        nome=folha.nome,
        referencia_tabela=primeira_referencia_tabela(lida.notas),
        data_tabela=primeira_data(lida.notas),
        ficheiro_origem=f"{Path(caminho).name}#{folha.folha}",
        ficheiro_hash=hash_conteudo([lida.cabecalho, *lida.linhas]),
        moeda="EUR",
        unidade_preco=UNIDADE,
        observacoes="\n".join(lida.notas) or None,
        artigos=tuple(artigos),
        avisos=tuple(avisos),
    )


def ler_tabelas(
    caminho: Path | str, folhas: Sequence[FolhaFinsa] | None = None
) -> list[TabelaCatalogo]:
    """As tabelas de FINSA de um ficheiro — uma por separador de ``FOLHAS``."""
    return [ler_folha(caminho, folha) for folha in (folhas or FOLHAS)]
