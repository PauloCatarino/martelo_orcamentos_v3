"""Sinónimos de pesquisa, construídos a partir do perfil de cada utilizador.

O que cada pessoa escreve em «Assistente — o meu perfil» passa a valer na
caixa de pesquisa: se disser que «guarda-fatos» é o mesmo que «roupeiro»,
procurar por um encontra o outro.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.domain.pesquisa_texto import forma_pesquisa
from app.services.ia_perfil_service import listar_entradas


#: Separadores usados quando se escrevem várias formas na mesma célula.
_SEPARADORES = re.compile(r"[;,/|]")

#: Quadros do perfil de onde se pode tirar sinónimos, e de que colunas.
#:
#: Só entram os quadros cuja segunda coluna é mesmo uma lista de formas
#: equivalentes. Em «Materiais», por exemplo, a segunda coluna é uma frase
#: explicativa — usá-la faria de «obra», «leva» e «cor» sinónimos de «lacado».
_QUADROS = {
    "movel": ("expressao", "significado"),
    "cliente": ("expressao", "significado"),
    "pessoa": ("expressao", "significado"),
    "material": ("expressao",),
}


def _formas(valor: str | None) -> list[str]:
    """Separa uma célula em formas equivalentes («a Viva; o JF»)."""
    if not valor:
        return []
    return [parte.strip() for parte in _SEPARADORES.split(valor) if parte.strip()]


#: Uma linha com mais formas do que isto é uma lista de vocabulário («roupeiro;
#: abrir; correr; cozinha; cama…»), não um grupo de sinónimos. Tratada como
#: sinónimos, procurar «cozinha» devolvia todos os roupeiros.
MAXIMO_FORMAS = 6

Forma = tuple[str, ...]


def grupos_de_sinonimos(entradas) -> list[frozenset[Forma]]:
    """Agrupa, por linha do perfil, as formas que valem umas pelas outras.

    Cada forma é a frase toda («guarda-fatos» → ``("guarda", "fato")``), sem
    palavras de ligação («a Viva» → ``("viva",)``). Antes cada palavra valia
    sozinha, e «Móveis J.F. Viva» fazia de «a» e «móveis» sinónimos de «viva».
    """
    grupos: list[frozenset[Forma]] = []
    for entrada in entradas:
        colunas = _QUADROS.get(entrada.tipo)
        if not colunas:
            continue

        formas: set[Forma] = set()
        for coluna in colunas:
            for texto in _formas(getattr(entrada, coluna, None)):
                forma = forma_pesquisa(texto)
                if forma:
                    formas.add(forma)

        # Uma forma sozinha não é sinónimo de nada; muitas são uma lista.
        if 1 < len(formas) <= MAXIMO_FORMAS:
            grupos.append(frozenset(formas))
    return grupos


def mapa_de_sinonimos(grupos) -> dict[Forma, frozenset[Forma]]:
    """Converte grupos em «forma -> formas que também servem»."""
    mapa: dict[Forma, set[Forma]] = {}
    for grupo in grupos:
        for forma in grupo:
            mapa.setdefault(forma, set()).update(grupo)
    return {forma: frozenset(alternativas) for forma, alternativas in mapa.items()}


def carregar_sinonimos(session: Session, user_id: int | None) -> dict[Forma, frozenset[Forma]]:
    """Sinónimos de um utilizador; vazio quando não há sessão ou perfil."""
    if not user_id:
        return {}
    return mapa_de_sinonimos(grupos_de_sinonimos(listar_entradas(session, user_id)))
