"""Que palavras de um texto o corretor ortográfico deve verificar.

As descrições do Martelo não são texto corrido: misturam frases com códigos de
material (``AGL_MLM_LINHO_CANCUN_19MM``), referências (``H3395/ST12_19mm``,
``H3170``), medidas (``2x600``), emails e siglas (``MDF``, ``ABS``). Sublinhar
isso tudo a vermelho tornava o corretor inútil ao fim de um dia.

Regras (pedido do Paulo, 16-09-2026):

- um bloco com algarismos, ``_``, ``/``, barra invertida, ``@``, ``.`` ou ``#`` no meio
  é um código, e não se verifica;
- palavras com 1 ou 2 letras não se verificam;
- siglas em MAIÚSCULAS até 3 letras (``MLM``, ``AGL``, ``PUX``) não se
  verificam;
- palavras com maiúsculas a meio (``iMos``, ``CutRite``) são nomes de programas;
- as restantes palavras em MAIÚSCULAS **verificam-se**: o corretor do Windows
  ignora-as por defeito, e nas descrições quase tudo está em maiúsculas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: Um bloco é tudo o que está entre espaços.
_BLOCO = re.compile(r"\S+")

#: Pontuação que pode rodear uma palavra sem fazer parte dela.
_PONTUACAO = ".,;:!?()[]{}«»\"'“”‘’…*-–—"

#: Caracteres que, no meio de um bloco, fazem dele um código.
_DE_CODIGO = re.compile(r"[\d_/\@.#+=&%$€<>|~^]")

#: Uma palavra: letras (com acentos), com hífen ou apóstrofo pelo meio.
_PALAVRA = re.compile(r"^[^\W\d_]+(?:[-'’][^\W\d_]+)*$")

TAMANHO_MINIMO = 3
TAMANHO_MAXIMO_SIGLA = 3


@dataclass(frozen=True)
class Palavra:
    inicio: int
    fim: int
    texto: str

    @property
    def tamanho(self) -> int:
        return self.fim - self.inicio


def palavras_a_verificar(texto: str) -> list[Palavra]:
    """As palavras do texto que fazem sentido passar pelo corretor."""
    palavras: list[Palavra] = []
    for bloco in _BLOCO.finditer(texto or ""):
        cru = bloco.group()
        esquerda = len(cru) - len(cru.lstrip(_PONTUACAO))
        nucleo = cru.strip(_PONTUACAO)
        if not nucleo or _DE_CODIGO.search(nucleo):
            continue
        if not _PALAVRA.match(nucleo) or not deve_verificar(nucleo):
            continue
        inicio = bloco.start() + esquerda
        palavras.append(Palavra(inicio, inicio + len(nucleo), nucleo))
    return palavras


def palavra_em(texto: str, posicao: int) -> Palavra | None:
    """A palavra verificável que contém ``posicao`` (para o botão direito)."""
    for palavra in palavras_a_verificar(texto):
        if palavra.inicio <= posicao <= palavra.fim:
            return palavra
    return None


def deve_verificar(palavra: str) -> bool:
    letras = sum(1 for c in palavra if c.isalpha())
    if letras < TAMANHO_MINIMO:
        return False
    if palavra.isupper():
        return letras > TAMANHO_MAXIMO_SIGLA
    # iMos, CutRite, McDonald: maiúsculas depois da primeira letra.
    if any(c.isupper() for c in palavra[1:]):
        return False
    return True


def chave_dicionario(palavra: str) -> str:
    """Como a palavra fica no dicionário da casa: sem distinguir maiúsculas."""
    return (palavra or "").strip().casefold()


def formas_a_tentar(palavra: str) -> list[str]:
    """As grafias a pedir ao corretor.

    ``LISBOA`` não existe em minúsculas, mas ``Lisboa`` existe; ``MONTAJEM``
    tem de ser perguntada em minúsculas porque o Windows aceita tudo o que
    vem em maiúsculas.
    """
    if palavra.isupper():
        return [palavra.lower(), palavra.capitalize()]
    return [palavra]


def acertar_caixa(sugestao: str, original: str) -> str:
    """Devolver a sugestão com as maiúsculas da palavra que se escreveu."""
    if original.isupper():
        return sugestao.upper()
    if original[:1].isupper():
        return sugestao[:1].upper() + sugestao[1:]
    return sugestao
