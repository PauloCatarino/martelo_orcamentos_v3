"""Separadores de placas em que as espessuras são colunas — e o unpivot.

Quase todos os fornecedores de placas escrevem a tabela da mesma maneira: uma
linha por decorativo e, à direita, um par de colunas por espessura —
``Esp 19mm`` a dizer se existe e ``Preço Tabela 19mm`` a dizer quanto custa. O
``Stock_B&F_Finsa`` leva isso a quarenta colunas; a Innovus dispensa a coluna
``Esp`` e deixa que a célula de preço vazia diga que aquela espessura não
existe.

Este módulo faz o **unpivot**: transforma cada par numa linha própria. É o que
permite perguntar «quanto custa o 19 mm em qualquer fornecedor» em vez de
procurar coluna a coluna. O ``egger.py``, o ``innovus.py`` e o ``finsa.py`` só
decidem o que fazer com as colunas da esquerda.

A parte de abrir o ficheiro e encontrar o cabeçalho está no ``excel.py``, que
as ferragens também usam.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from app.services.catalogos import excel
from app.services.catalogos.base import FormatoInesperado, normalizar, numero
from app.services.catalogos.excel import FolhaExcel, valor

__all__ = [
    "FolhaPlacas",
    "FormatoInesperado",
    "ParEspessura",
    "PrecoEspessura",
    "desdobrar",
    "ler_folha",
    "valor",
]

#: Reconhece «Esp 19mm», «Espessura 19 mm», «19mm».
_ESPESSURA = re.compile(r"(\d+(?:[.,]\d+)?)\s*mm")

#: O que conta como coluna de preço. Uma lição do leitor antigo, que só
#: aceitava «preco tabela» e «pvp» e por isso nunca leu os preços do BLUM.
_PRECOS = ("preco tabela", "preco", "pvp", "valor", "eur")

#: O que conta como marca de disponibilidade numa coluna «Esp NNmm».
_EXISTE = {"sim", "s", "x", "1", "true", "yes", "ok", "disponivel"}
_NAO_EXISTE = {"nao", "n", "0", "false", "no", "-", ""}


@dataclass(frozen=True)
class ParEspessura:
    """Um par ``Esp NNmm`` / ``Preço Tabela NNmm`` do cabeçalho."""

    espessura_mm: Decimal
    etiqueta: str
    coluna_preco: int
    #: Nulo quando o fornecedor só dá preço, sem coluna a dizer se existe.
    coluna_flag: int | None = None


@dataclass(frozen=True)
class FolhaPlacas(FolhaExcel):
    """Um separador de placas, com os pares de espessura já mapeados."""

    espessuras: tuple[ParEspessura, ...] = ()


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
    """Lê um separador de placas e devolve-o com as espessuras mapeadas.

    Levanta ``FormatoInesperado`` pelas razões do ``excel.ler_folha`` e ainda
    quando não há pares de espessura nenhuns — sinal de que o separador não é
    deste feitio, ou de que o cabeçalho mudou de palavra.
    """
    lida = excel.ler_folha(caminho, nome_folha)
    espessuras = _mapear_espessuras(lida.cabecalho)
    if not espessuras:
        raise FormatoInesperado(
            f"{nome_folha}: nenhuma coluna de preço com espessura em mm. "
            f"O cabeçalho tem: {', '.join(lida.cabecalho)}"
        )
    return FolhaPlacas(
        nome=lida.nome,
        notas=lida.notas,
        cabecalho=lida.cabecalho,
        linhas=lida.linhas,
        indices=lida.indices,
        espessuras=espessuras,
    )


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
