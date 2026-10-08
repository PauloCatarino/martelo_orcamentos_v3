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

#: A partir deste tamanho, um termo que não exista tal e qual ainda encontra
#: as palavras que COMEÇAM por ele («cancu» encontra «cancun») e, se for só
#: algarismos, as que o CONTÊM («877» encontra o orçamento «260877»). Abaixo
#: disto exige-se a palavra inteira, senão uma ou duas letras devolviam a lista
#: toda.
_MINIMO_PARCIAL = 3

#: Letras coladas a algarismos («4gavetas», «1460x600mm») separam-se, para
#: «gaveta» e «600» encontrarem a palavra.
_FRONTEIRA_LETRA_ALGARISMO = re.compile(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])")

#: Palavras de ligação e pedidos («quero ver as obras da…») que não são termo de
#: procura. Sem isto, escrever uma frase obrigava cada obra a ter «da», «com» e
#: «obras» — e as frases não encontravam nada.
PALAVRAS_VAZIAS: frozenset[str] = frozenset(
    {
        "a", "o", "os", "as", "um", "uma", "uns", "umas", "ao", "aos",
        "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
        "com", "para", "pra", "por", "pelo", "pela", "pelos", "pelas",
        "e", "ou", "que", "me",
        "obra", "obras", "processo", "processos",
        "quero", "queria", "ver", "mostra", "mostrar", "mostre",
        "procura", "procurar", "encontra", "encontrar",
        "lista", "listar", "qual", "quais", "quantas", "quantos",
        "ha", "tem", "temos", "tenho", "leva", "levam", "levem",
        "esta", "estao", "sao", "todas", "todos",
        "este", "estes", "esta", "estas", "esse", "esses",
        "cliente", "clientes",
    }
)


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


_RAIZES_VAZIAS: frozenset[str] = frozenset(raiz(p) for p in PALAVRAS_VAZIAS)


def raizes_pesquisa(texto: object) -> list[str]:
    """Raízes para pesquisar: como ``raizes``, mas descola letras de algarismos.

    «4gavetas» dá ``["4", "gaveta"]``. Usa-se dos dois lados da comparação
    (obra e pesquisa), por isso «19mm» continua a encontrar «19mm».
    """
    texto = _FRONTEIRA_LETRA_ALGARISMO.sub(" ", normalizar(texto))
    return [raiz(palavra) for palavra in texto.split()]


def palavras_procuradas(texto: object) -> list[str]:
    """Raízes que contam numa pesquisa: sem palavras de ligação.

    Se só houver palavras de ligação («de»), procura-se por elas mesmo — mais
    vale isso do que fingir que a caixa está vazia.
    """
    todas = raizes_pesquisa(texto)
    uteis = [palavra for palavra in todas if palavra not in _RAIZES_VAZIAS]
    return uteis or todas


def forma_pesquisa(texto: object) -> tuple[str, ...]:
    """Uma forma escrita («guarda-fatos», «a Viva») como sequência de raízes."""
    return tuple(palavras_procuradas(texto))


def indexar(textos) -> frozenset[str]:
    """Constrói o conjunto de raízes de uma obra, para comparar depressa."""
    conjunto: set[str] = set()
    for texto in textos:
        conjunto.update(raizes_pesquisa(texto))
    return frozenset(conjunto)


def _mapa_de_formas(sinonimos) -> dict[tuple[str, ...], frozenset[tuple[str, ...]]]:
    """Aceita o mapa antigo (``raiz -> raízes``) e o novo (``forma -> formas``)."""
    def _forma(valor) -> tuple[str, ...]:
        return valor if isinstance(valor, tuple) else (valor,)

    return {
        _forma(chave): frozenset(_forma(valor) for valor in valores)
        for chave, valores in (sinonimos or {}).items()
    }


def expandir_termos(texto: object, sinonimos=None) -> list[frozenset]:
    """Devolve, para cada palavra escrita, as alternativas que a satisfazem.

    Cada elemento da lista é um conjunto: basta **uma** das suas alternativas
    estar na obra. Entre elementos, é obrigatório que **todos** sejam
    satisfeitos. Uma alternativa é uma raiz (``"roupeiro"``) ou, quando o
    sinónimo tem várias palavras, um tuplo delas (``("guarda", "fato")``), que
    só conta se a obra as tiver todas.

    Os sinónimos de várias palavras também se reconhecem quando são escritos:
    «guarda-fatos» vira um só termo, e não «guarda» E «fatos».
    """
    formas = _mapa_de_formas(sinonimos)
    maior = max((len(chave) for chave in formas), default=1)
    palavras = palavras_procuradas(texto)

    termos: list[frozenset] = []
    i = 0
    while i < len(palavras):
        for tamanho in range(min(maior, len(palavras) - i), 0, -1):
            chave = tuple(palavras[i : i + tamanho])
            if tamanho == 1 or chave in formas:
                break
        alternativas = {chave} | set(formas.get(chave, ()))
        termos.append(
            frozenset(a[0] if len(a) == 1 else a for a in alternativas)
        )
        i += tamanho
    return termos


def corresponde(indice: frozenset[str], termos) -> bool:
    """True quando a obra satisfaz todas as palavras escritas.

    Cada palavra é procurada primeiro tal e qual (raiz igual a raiz, que é
    barato) e só depois como pedaço de uma palavra maior. É o que faz «877»
    encontrar o orçamento «260877»: raramente se escreve o número todo.
    """
    return all(
        any(_alternativa_casa(indice, alternativa) for alternativa in alternativas)
        for alternativas in termos
    )


def _alternativa_casa(indice: frozenset[str], alternativa) -> bool:
    if isinstance(alternativa, tuple):
        return all(palavra_casa(indice, palavra) for palavra in alternativa)
    return palavra_casa(indice, alternativa)


def palavra_casa(indice, termo: str) -> bool:
    """True quando a palavra está na obra, inteira ou por pedaço.

    Por pedaço quer dizer: o **início** de uma palavra («roup» → «roupeiro»), ou
    qualquer parte de um número («877» → «260877»). No meio de uma palavra não:
    «laca» encontrava «contraplacado» e «porta» encontrava «transportadora».
    """
    if termo in indice:
        return True
    if len(termo) < _MINIMO_PARCIAL:
        return False
    if termo.isdigit():
        return any(termo in indexada for indexada in indice)
    return any(indexada.startswith(termo) for indexada in indice)


def contem_parcial(vocabulario, palavra: str) -> bool:
    """True quando a palavra escrita é pedaço de algo que existe mesmo."""
    alvo = raiz(normalizar(palavra))
    if len(alvo) < _MINIMO_PARCIAL:
        return False
    return palavra_casa(vocabulario, alvo)


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
        # Uma palavra que exista — inteira ou como pedaço de outra — não se
        # corrige: senão «877» dava o disparate «Quis dizer 77?». As palavras
        # de ligação também não, porque a pesquisa nem olha para elas.
        if (
            raiz(palavra) in _RAIZES_VAZIAS
            or raiz(palavra) in vocabulario
            or contem_parcial(vocabulario, palavra)
        ):
            sugestao.append(palavra)
            continue
        proxima = sugerir_termo(palavra, vocabulario)
        if proxima:
            sugestao.append(proxima)
            mudou = True
        else:
            sugestao.append(palavra)

    return " ".join(sugestao) if mudou else ""
