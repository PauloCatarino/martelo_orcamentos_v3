"""Sinónimos de pesquisa, construídos a partir do perfil de cada utilizador.

O que cada pessoa escreve em «Assistente — o meu perfil» passa a valer na
caixa de pesquisa: se disser que «guarda-fatos» é o mesmo que «roupeiro»,
procurar por um encontra o outro.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.domain.pesquisa_texto import raizes
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


def grupos_de_sinonimos(entradas) -> list[frozenset[str]]:
    """Agrupa, por linha do perfil, as raízes que valem umas pelas outras."""
    grupos: list[frozenset[str]] = []
    for entrada in entradas:
        colunas = _QUADROS.get(entrada.tipo)
        if not colunas:
            continue

        palavras: set[str] = set()
        for coluna in colunas:
            for forma in _formas(getattr(entrada, coluna, None)):
                palavras.update(raizes(forma))

        # Uma palavra sozinha não é sinónimo de nada.
        if len(palavras) > 1:
            grupos.append(frozenset(palavras))
    return grupos


def mapa_de_sinonimos(grupos) -> dict[str, frozenset[str]]:
    """Converte grupos em «raiz -> raízes que também servem»."""
    mapa: dict[str, set[str]] = {}
    for grupo in grupos:
        for palavra in grupo:
            mapa.setdefault(palavra, set()).update(grupo)
    return {palavra: frozenset(alternativas) for palavra, alternativas in mapa.items()}


def carregar_sinonimos(session: Session, user_id: int | None) -> dict[str, frozenset[str]]:
    """Sinónimos de um utilizador; vazio quando não há sessão ou perfil."""
    if not user_id:
        return {}
    return mapa_de_sinonimos(grupos_de_sinonimos(listar_entradas(session, user_id)))
