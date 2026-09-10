"""Ler um separador de placas em que as espessuras são colunas.

Quase todos os fornecedores de placas escrevem a tabela da mesma maneira: uma
linha por decorativo e, à direita, um par de colunas por espessura —
``Esp 19mm`` a dizer se existe e ``Preço Tabela 19mm`` a dizer quanto custa. O
Stock_B&F_Finsa leva isso a quarenta colunas.

Este módulo é a parte que não muda de fornecedor para fornecedor: encontra o
cabeçalho, descobre que pares de espessura existem, e faz o **unpivot** —
transforma cada par numa linha própria. É o que permite perguntar «quanto custa
o 19 mm em qualquer fornecedor» em vez de procurar coluna a coluna. O
``egger.py`` (e depois o Sonae/Innovus e a Finsa) só decide o que fazer com as
colunas da esquerda.

O cabeçalho é reconhecido por qualquer célula que contenha ``refer`` já sem
acentos — ``Referência``, ``REFERENCIA``, ``Ref.`` e ``Ref`` entram todas. E
quando não se encontra, isto **rebenta**: era exatamente aqui que o leitor
antigo devolvia zero linhas sem dizer nada.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from app.services.catalogos.base import FormatoInesperado, normalizar, numero, texto

#: Até onde se procura o cabeçalho. Os separadores põem título e notas em cima
#: (o do Egger usa três linhas); doze dá folga sem chegar aos dados.
LINHAS_PARA_CABECALHO = 12

#: Reconhece «Esp 19mm», «Espessura 19 mm», «19mm».
_ESPESSURA = re.compile(r"(\d+(?:[.,]\d+)?)\s*mm")

#: O que conta como coluna de preço. Uma lição do leitor antigo, que só
#: aceitava «preco tabela» e «pvp» e por isso nunca leu os preços do BLUM.
_PRECOS = ("preco tabela", "preco", "pvp", "valor", "eur")

#: O que conta como marca de disponibilidade numa coluna «Esp NNmm».
_EXISTE = {"sim", "s", "x", "1", "true", "yes", "ok", "disponivel"}
_NAO_EXISTE = {"nao", "n", "0", "false", "no", "-", ""}


@dataclass(frozen=True, slots=True)
class ParEspessura:
    """Um par ``Esp NNmm`` / ``Preço Tabela NNmm`` do cabeçalho."""

    espessura_mm: Decimal
    etiqueta: str
    coluna_preco: int
    #: Nulo quando o fornecedor só dá preço, sem coluna a dizer se existe.
    coluna_flag: int | None = None


@dataclass(frozen=True, slots=True)
class FolhaPlacas:
    """Um separador já arrumado: notas, cabeçalho, linhas e espessuras."""

    nome: str
    #: As linhas acima do cabeçalho — título, data da tabela, critérios.
    notas: tuple[str, ...]
    cabecalho: tuple[str, ...]
    #: Só as linhas com conteúdo, tal como vieram (sem unpivot).
    linhas: tuple[tuple[object, ...], ...]
    espessuras: tuple[ParEspessura, ...]
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


def _e_cabecalho(valores: Sequence[object]) -> bool:
    preenchidas = [v for v in valores if texto(v) is not None]
    if len(preenchidas) < 4:
        return False
    return any("refer" in normalizar(v) for v in valores)


def _mapear_espessuras(cabecalho: Sequence[str]) -> tuple[ParEspessura, ...]:
    """Descobre os pares de espessura, emparelhando preço com disponibilidade."""
    flags: dict[str, int] = {}
    precos: list[tuple[str, Decimal, int]] = []

    for indice, cabeca in enumerate(cabecalho):
        norm = normalizar(cabeca)
        achado = _ESPESSURA.search(norm)
        if not achado:
            continue
        bruto = achado.group(1).replace(",", ".")
        etiqueta = f"{Decimal(bruto).normalize():f}mm"
        if any(marca in norm for marca in _PRECOS):
            precos.append((etiqueta, Decimal(bruto), indice))
        elif norm.startswith("esp"):
            flags.setdefault(etiqueta, indice)

    return tuple(
        ParEspessura(
            espessura_mm=espessura,
            etiqueta=etiqueta,
            coluna_preco=indice,
            coluna_flag=flags.get(etiqueta),
        )
        for etiqueta, espessura, indice in precos
    )


def ler_folha(caminho: Path | str, nome_folha: str) -> FolhaPlacas:
    """Lê um separador de placas e devolve-o arrumado.

    Levanta ``FormatoInesperado`` se o separador não existir, se não houver
    cabeçalho reconhecível, se não houver pares de espessura ou se não sobrar
    linha nenhuma com conteúdo.
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

    espessuras = _mapear_espessuras(cabecalho)
    if not espessuras:
        raise FormatoInesperado(
            f"{nome_folha}: nenhuma coluna de preço com espessura em mm. "
            f"O cabeçalho tem: {', '.join(cabecalho)}"
        )

    linhas = tuple(
        linha
        for linha in todas[indice_cabecalho + 1 :]
        if any(texto(c) is not None for c in linha)
    )
    if not linhas:
        raise FormatoInesperado(f"{nome_folha}: cabeçalho encontrado mas zero linhas")

    return FolhaPlacas(
        nome=nome_folha,
        notas=notas,
        cabecalho=cabecalho,
        linhas=linhas,
        espessuras=espessuras,
        indices=indices,
    )


def valor(linha: Sequence[object], indice: int | None) -> object:
    """A célula, ou ``None`` se a coluna não existe ou a linha é mais curta."""
    if indice is None or indice >= len(linha):
        return None
    return linha[indice]


@dataclass(frozen=True, slots=True)
class PrecoEspessura:
    """O resultado do unpivot de uma linha: uma espessura e o seu preço."""

    espessura_mm: Decimal
    etiqueta: str
    preco: Decimal | None
    #: Aviso quando a disponibilidade e o preço se desdizem. Ver ``desdobrar``.
    aviso: str | None = None


def desdobrar(folha: FolhaPlacas, linha: Sequence[object]) -> list[PrecoEspessura]:
    """O unpivot de uma linha: um ``PrecoEspessura`` por espessura que existe.

    Uma espessura entra quando a coluna ``Esp NNmm`` diz que sim **ou** quando
    há preço — nunca se descarta um preço só porque a coluna do lado estava
    vazia. Quando as duas se desdizem sai um aviso, porque é sinal de que a
    tabela mudou de forma e alguém tem de olhar para ela.
    """
    resultado: list[PrecoEspessura] = []
    for par in folha.espessuras:
        preco = numero(valor(linha, par.coluna_preco))
        bruto = valor(linha, par.coluna_flag) if par.coluna_flag is not None else None
        marca = normalizar(bruto)

        if par.coluna_flag is None:
            existe = preco is not None
        elif marca in _EXISTE:
            existe = True
        elif marca in _NAO_EXISTE:
            existe = False
        else:
            # Marca que não se reconhece: dá-se-lhe o benefício da dúvida se
            # houver preço, para não se perder dinheiro por causa de uma
            # palavra nova numa coluna.
            existe = preco is not None

        aviso: str | None = None
        if existe and preco is None and par.coluna_flag is not None:
            aviso = f"{par.etiqueta}: marcado como disponível mas sem preço"
        elif not existe and preco is not None:
            aviso = f"{par.etiqueta}: tem preço mas a coluna Esp diz {bruto!r}"
            existe = True

        if existe:
            resultado.append(
                PrecoEspessura(
                    espessura_mm=par.espessura_mm,
                    etiqueta=par.etiqueta,
                    preco=preco,
                    aviso=aviso,
                )
            )
    return resultado
