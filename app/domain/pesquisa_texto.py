"""Motor de pesquisa por texto: acentos, pontuação, plurais e sinónimos.

Regras fixas, sem modelo de linguagem: é o que vai buscar as obras, tanto
quando o utilizador escreve na caixa de pesquisa como (mais tarde) quando o
assistente decidir que filtros aplicar.

A ideia central é comparar **raízes** em vez de palavras: «roupeiros» e
«roupeiro» reduzem-se ambos a ``roupeir``, por isso encontram-se um ao outro.
Como a redução é aplicada dos dois lados da comparação, uma raiz linguisticamente
errada continua a funcionar — só torna a pesquisa um pouco mais abrangente.
"""

from __future__ import annotations

import difflib
import re
import unicodedata


#: Tudo o que não é letra sem acento nem dígito conta como separador.
_PONTUACAO = re.compile(r"[^0-9a-z]+")

#: Terminações de plural português, da mais específica para a mais genérica.
_PLURAIS: tuple[tuple[str, str], ...] = (
    ("oes", "ao"),   # aviões -> aviao
    ("aes", "ao"),   # pães -> pao
    ("ais", "al"),   # metais -> metal
    ("eis", "el"),   # móveis -> movel
    ("ois", "ol"),   # lençóis -> lencol
    ("uis", "ul"),   # azuis -> azul
)

#: Abaixo deste tamanho não se corta nada (evita estragar códigos e siglas).
_MINIMO_RAIZ = 4


def normalizar(valor: object) -> str:
    """Minúsculas, sem acentos e com a pontuação transformada em espaço."""
    if valor is None:
        return ""

    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return _PONTUACAO.sub(" ", texto).strip()


def raiz(palavra: str) -> str:
    """Reduz uma palavra à sua raiz, tirando o plural mais comum."""
    if len(palavra) < _MINIMO_RAIZ:
        return palavra

    for fim, troca in _PLURAIS:
        if palavra.endswith(fim) and len(palavra) > len(fim) + 1:
            return palavra[: -len(fim)] + troca

    if palavra.endswith("ns") and len(palavra) > 3:
        return palavra[:-2] + "m"  # homens -> homem
    if palavra.endswith("es") and len(palavra) > 4:
        return palavra[:-2]  # pincéis já apanhado acima; luzes -> luz
    if palavra.endswith("s") and len(palavra) > 3:
        return palavra[:-1]  # portas -> porta
    return palavra


def raizes(texto: object) -> list[str]:
    """Normaliza e devolve a raiz de cada palavra, pela ordem de escrita."""
    return [raiz(palavra) for palavra in normalizar(texto).split()]


def indexar(textos) -> frozenset[str]:
    """Constrói o conjunto de raízes de uma obra, para comparar depressa."""
    conjunto: set[str] = set()
    for texto in textos:
        conjunto.update(raizes(texto))
    return frozenset(conjunto)


def expandir_termos(texto: object, sinonimos=None) -> list[frozenset[str]]:
    """Devolve, para cada palavra escrita, as raízes que a satisfazem.

    Cada elemento da lista é um conjunto: basta **uma** das suas raízes estar
    na obra. Entre elementos, é obrigatório que **todos** sejam satisfeitos.
    """
    sinonimos = sinonimos or {}
    termos: list[frozenset[str]] = []
    for palavra in raizes(texto):
        alternativas = {palavra}
        alternativas.update(sinonimos.get(palavra, ()))
        termos.append(frozenset(alternativas))
    return termos


def corresponde(indice: frozenset[str], termos) -> bool:
    """True quando a obra satisfaz todas as palavras escritas."""
    return all(alternativas & indice for alternativas in termos)


def corresponde_texto(textos, texto: object, sinonimos=None) -> bool:
    """Atalho para comparar sem índice pré-construído."""
    termos = expandir_termos(texto, sinonimos)
    if not termos:
        return True
    return corresponde(indexar(textos), termos)


def sugerir_termo(palavra: str, vocabulario, limite: float = 0.75) -> str:
    """Palavra parecida existente no vocabulário, para o «quis dizer…».

    Só é usada quando a pesquisa não devolveu nada: assim o custo de comparar
    com todo o vocabulário só se paga quando já não há nada a perder.
    """
    alvo = raiz(normalizar(palavra))
    if not alvo:
        return ""

    proximas = difflib.get_close_matches(alvo, list(vocabulario), n=1, cutoff=limite)
    return proximas[0] if proximas else ""


def sugerir_pesquisa(texto: object, vocabulario) -> str:
    """Reescreve a pesquisa com as palavras parecidas que existem mesmo."""
    palavras = normalizar(texto).split()
    if not palavras:
        return ""

    vocabulario = set(vocabulario)
    sugestao: list[str] = []
    mudou = False
    for palavra in palavras:
        if raiz(palavra) in vocabulario:
            sugestao.append(palavra)
            continue
        proxima = sugerir_termo(palavra, vocabulario)
        if proxima:
            sugestao.append(proxima)
            mudou = True
        else:
            sugestao.append(palavra)

    return " ".join(sugestao) if mudou else ""
