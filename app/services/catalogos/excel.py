"""Abrir um separador de Excel de fornecedor e encontrar-lhe o cabeçalho.

Isto é a parte que não muda nem de fornecedor nem de tipo de produto: saltar as
linhas de título e de notas que vêm no topo, reconhecer a linha do cabeçalho,
e dar uma maneira de procurar uma coluna pelo nome sem ter de saber como é que
aquele fornecedor a escreveu.

Em cima disto assentam duas camadas:

* ``excel_placas`` — separadores em que as espessuras são **colunas** e cada
  linha se desdobra em várias (EGGER, Innovus, Finsa);
* ``ferragens`` — separadores em que cada linha é **um** artigo com **um**
  preço (Emuca, Fiware, BLUM, Casa Trend).

O cabeçalho é reconhecido por qualquer célula que contenha ``refer`` já sem
acentos — ``Referência``, ``REFERENCIA``, ``Ref.``, ``Ref`` e ``Referência
Artigo`` entram todas. E quando não se encontra, isto **rebenta**: era
exatamente aqui que o leitor antigo devolvia zero linhas sem dizer nada, e
3 869 artigos ficaram invisíveis na Pesquisa IA sem ninguém saber.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from openpyxl import load_workbook

from app.services.catalogos.base import FormatoInesperado, normalizar, texto

#: Até onde se procura o cabeçalho. Os separadores põem título e notas em cima
#: — o do EGGER usa três linhas, os da Innovus seis. Doze dá folga sem chegar
#: aos dados.
LINHAS_PARA_CABECALHO = 12


@dataclass(frozen=True)
class FolhaExcel:
    """Um separador já arrumado: notas, cabeçalho e linhas com conteúdo."""

    nome: str
    #: As linhas acima do cabeçalho — título, data da tabela, critérios.
    notas: tuple[str, ...]
    cabecalho: tuple[str, ...]
    linhas: tuple[tuple[object, ...], ...]
    #: Cabeçalho normalizado -> índice, para o ``coluna()``.
    indices: dict[str, int]

    def coluna(self, *nomes: str) -> int | None:
        """O índice da coluna que corresponde ao primeiro nome que encaixar.

        Tenta a igualdade antes da inclusão, e por essa ordem para todos os
        nomes: senão procurar por ``"st"`` apanhava um ``Stock`` que estivesse
        mais à esquerda em vez da coluna ``ST``.
        """
        for comparar in (
            lambda alvo, cabeca: alvo == cabeca,
            lambda alvo, cabeca: alvo in cabeca,
        ):
            for nome in nomes:
                alvo = normalizar(nome)
                if not alvo:
                    continue
                for cabeca, indice in self.indices.items():
                    if comparar(alvo, cabeca):
                        return indice
        return None

    def exigir_coluna(self, *nomes: str) -> int:
        """Como ``coluna()``, mas rebenta em vez de devolver ``None``."""
        indice = self.coluna(*nomes)
        if indice is None:
            raise FormatoInesperado(
                f"{self.nome}: não há coluna para {' / '.join(nomes)}. "
                f"O cabeçalho tem: {', '.join(self.cabecalho)}"
            )
        return indice


def valor(linha: Sequence[object], indice: int | None) -> object:
    """A célula, ou ``None`` se a coluna não existe ou a linha é mais curta."""
    if indice is None or indice >= len(linha):
        return None
    return linha[indice]


def _e_cabecalho(valores: Sequence[object]) -> bool:
    preenchidas = [v for v in valores if texto(v) is not None]
    if len(preenchidas) < 4:
        return False
    return any("refer" in normalizar(v) for v in valores)


def ler_folha(caminho: Path | str, nome_folha: str) -> FolhaExcel:
    """Lê um separador e devolve-o arrumado.

    Levanta ``FormatoInesperado`` se o ficheiro ou o separador não existirem,
    se não houver cabeçalho reconhecível, ou se não sobrar linha nenhuma com
    conteúdo.
    """
    caminho = Path(caminho)
    if not caminho.exists():
        raise FormatoInesperado(f"ficheiro não encontrado: {caminho}")

    workbook = load_workbook(caminho, read_only=True, data_only=True)
    try:
        if nome_folha not in workbook.sheetnames:
            raise FormatoInesperado(
                f"o separador {nome_folha!r} não existe em {caminho.name}. "
                f"Existem: {', '.join(workbook.sheetnames)}"
            )
        worksheet = workbook[nome_folha]
        todas = [tuple(linha) for linha in worksheet.iter_rows(values_only=True)]
    finally:
        workbook.close()

    indice_cabecalho: int | None = None
    for i, linha in enumerate(todas[:LINHAS_PARA_CABECALHO]):
        if _e_cabecalho(linha):
            indice_cabecalho = i
            break

    if indice_cabecalho is None:
        raise FormatoInesperado(
            f"{nome_folha}: não se encontrou o cabeçalho nas primeiras "
            f"{LINHAS_PARA_CABECALHO} linhas (nenhuma célula com 'refer')"
        )

    cabecalho = tuple(texto(c) or "" for c in todas[indice_cabecalho])
    notas = tuple(
        nota
        for linha in todas[:indice_cabecalho]
        for nota in (texto(linha[0] if linha else None),)
        if nota
    )

    indices: dict[str, int] = {}
    for indice, cabeca in enumerate(cabecalho):
        norm = normalizar(cabeca)
        if norm:
            indices.setdefault(norm, indice)

    linhas = tuple(
        linha
        for linha in todas[indice_cabecalho + 1 :]
        if any(texto(c) is not None for c in linha)
    )
    if not linhas:
        raise FormatoInesperado(f"{nome_folha}: cabeçalho encontrado mas zero linhas")

    return FolhaExcel(
        nome=nome_folha,
        notas=notas,
        cabecalho=cabecalho,
        linhas=linhas,
        indices=indices,
    )
