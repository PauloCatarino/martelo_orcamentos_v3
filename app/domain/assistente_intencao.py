"""Cérebro do «IA Martelo» (Fase 1): traduzir uma pergunta em filtros.

Regras fixas, sem modelo de linguagem — tal como :mod:`app.domain.pesquisa_texto`.
O martelo **nunca inventa dados**: aqui só se decide QUE filtros aplicar
(estado, cliente, responsável, atrasadas e texto livre); é o código da Produção
que corre a consulta e devolve obras reais. O pior erro possível é propor a
lista errada, que o utilizador descarta.

O que o utilizador ensina em «Assistente — o meu perfil» entra por aqui: as
alcunhas de clientes e colegas, as expressões de estado («na máquina» =
Produção) e as palavras que ele próprio marcou como ambíguas (o martelo
pergunta em vez de adivinhar).

O LLM local e o boneco animado assentam POR CIMA deste núcleo, numa fase
seguinte; esta camada funciona offline e é 100% testável.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from app.domain.pesquisa_texto import normalizar, raiz

#: Estados canónicos e as formas de os dizer (sem acentos, minúsculas).
#:
#: «Obra fechada» = Arquivado (decisão do Paulo); Finalizado é distinto porque
#: ainda pode estar por levantar/faturar — ver ``prazos_producao``.
_ESTADOS_PADRAO: dict[str, frozenset[str]] = {
    "Desenho": frozenset(
        {"desenho", "desenhos", "preparacao", "a desenhar", "por desenhar"}
    ),
    "Producao": frozenset(
        {
            "producao",
            "em producao",
            "na maquina",
            "nas maquinas",
            "a produzir",
            "em fabrico",
            "na fabrica",
        }
    ),
    "Finalizado": frozenset(
        {
            "finalizado",
            "finalizada",
            "finalizadas",
            "terminado",
            "terminada",
            "concluido",
            "concluida",
            "pronto",
            "pronta",
        }
    ),
    "Arquivado": frozenset(
        {
            "arquivado",
            "arquivada",
            "arquivadas",
            "obra fechada",
            "obras fechadas",
            "fechada",
            "fechadas",
            "fechado",
        }
    ),
}

#: Raízes que significam «obra em atraso» (semáforo vermelho da entrega).
_RAIZES_ATRASO: frozenset[str] = frozenset({"atrasada", "atrasado", "atraso"})

#: Raízes possessivas de 1.ª pessoa («as minhas obras» = eu, o responsável).
_RAIZES_MINHAS: frozenset[str] = frozenset({"minha", "meu"})

#: Artigos iniciais a ignorar nas alcunhas do perfil («a Viva» casa «da Viva»).
_ARTIGOS: frozenset[str] = frozenset({"a", "o", "as", "os", "um", "uma"})

#: Palavras de ligação/verbos de pesquisa que não são termo de procura.
_VAZIAS: frozenset[str] = frozenset(
    {
        "a", "o", "os", "as", "um", "uma", "uns", "umas",
        "de", "do", "da", "dos", "das", "em", "no", "na", "nos", "nas",
        "com", "para", "pra", "por", "e", "que", "me", "the",
        "obra", "obras", "processo", "processos",
        "quero", "queria", "ver", "mostra", "mostrar", "mostre",
        "lista", "listar", "diz", "dizer", "quais", "quantas", "quantos",
        "ha", "tem", "temos", "estao", "esta", "sao", "todas", "todos",
        "esta", "este", "estes", "estas",
    }
)

#: Pistas de papel: se aparecerem, tiram a ambiguidade cliente/pessoa.
_PISTAS_CLIENTE: frozenset[str] = frozenset({"cliente", "clientes"})
_PISTAS_RESPONSAVEL: frozenset[str] = frozenset(
    {"responsavel", "responsaveis", "resp", "colega", "colegas"}
)


@dataclass(frozen=True)
class PerfilVocabulario:
    """Vocabulário do utilizador, já normalizado, vindo do «meu perfil».

    Cada mapa vai da forma escrita (normalizada) para o valor real: alcunha ->
    nome completo do cliente, «na máquina» -> ``Producao``, etc. ``ambiguas``
    guarda a pergunta que o próprio utilizador quer que o martelo faça.
    """

    estados: Mapping[str, str] = field(default_factory=dict)
    clientes: Mapping[str, str] = field(default_factory=dict)
    pessoas: Mapping[str, str] = field(default_factory=dict)
    ambiguas: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Intencao:
    """Filtros propostos para a pergunta, mais o que o martelo precisa de saber."""

    termos: str = ""
    estado: str | None = None
    cliente: str | None = None
    responsavel: str | None = None
    so_atrasadas: bool = False
    #: Perguntas de desambiguação (o martelo pergunta antes de assumir).
    perguntas: tuple[str, ...] = ()
    #: Palavras que o martelo não reconheceu (para o «quer ensinar-me?»).
    desconhecidas: tuple[str, ...] = ()

    @property
    def precisa_perguntar(self) -> bool:
        return bool(self.perguntas)


def interpretar(
    pergunta: object,
    *,
    clientes: Iterable[str] = (),
    responsaveis: Iterable[str] = (),
    perfil: PerfilVocabulario | None = None,
    utilizador_sessao: str | None = None,
) -> Intencao:
    """Traduz uma pergunta em :class:`Intencao` (filtros da Produção).

    ``clientes`` e ``responsaveis`` são os valores reais presentes na lista, para
    o martelo casar nomes escritos por extenso mesmo sem estarem no perfil.
    ``utilizador_sessao`` é o nome do responsável com sessão iniciada, para
    «as minhas obras» filtrar por ele.
    """
    perfil = perfil or PerfilVocabulario()
    resto = f" {normalizar(pergunta)} "
    if not resto.strip():
        return Intencao()

    # Mapas de frase -> valor, das formas mais longas para as mais curtas, para
    # «obra fechada» ser apanhado antes de «fechada».
    estados = _mapa_estados(perfil)
    clientes_mapa = _mapa_valores(clientes, perfil.clientes)
    pessoas_mapa = _mapa_valores(responsaveis, perfil.pessoas)

    tem_pista_cliente = _tem_alguma(resto, _PISTAS_CLIENTE)
    tem_pista_responsavel = _tem_alguma(resto, _PISTAS_RESPONSAVEL)

    perguntas: list[str] = []

    # 1) Estado (frases primeiro).
    estado, resto = _extrair_frase(resto, estados)

    # 2) Ambiguidade declarada pelo utilizador («Silva») — pergunta e não assume.
    for forma, questao in _ordenar_por_tamanho(perfil.ambiguas):
        if _contem_frase(resto, forma):
            perguntas.append(questao)
            resto = _remover_frase(resto, forma)

    # 3) Cliente e responsável. Uma forma que sirva os dois é ambígua, a menos
    #    que a pergunta traga uma pista de papel («cliente Silva»).
    cliente = None
    responsavel = None
    for forma, valor in _ordenar_por_tamanho(clientes_mapa):
        if not _contem_frase(resto, forma):
            continue
        tambem_pessoa = forma in pessoas_mapa
        if tambem_pessoa and not tem_pista_cliente and not tem_pista_responsavel:
            perguntas.append(
                f"«{forma}» é o cliente ou a pessoa responsável?"
            )
            resto = _remover_frase(resto, forma)
            continue
        if tambem_pessoa and tem_pista_responsavel and not tem_pista_cliente:
            continue  # a pista diz que é a pessoa; trata-se abaixo
        if cliente is None:
            cliente = valor
        resto = _remover_frase(resto, forma)

    for forma, valor in _ordenar_por_tamanho(pessoas_mapa):
        if not _contem_frase(resto, forma):
            continue
        if responsavel is None:
            responsavel = valor
        resto = _remover_frase(resto, forma)

    # 3b) «as minhas obras» = o utilizador da sessão, se não houver outro nome.
    possessivo, resto = _extrair_possessivo(resto)
    if responsavel is None and possessivo and utilizador_sessao:
        responsavel = str(utilizador_sessao).strip()

    # 4) Atrasadas e limpeza de palavras vazias; o que sobra é texto livre.
    so_atrasadas, resto = _extrair_atraso(resto)
    termos, desconhecidas = _termos_e_desconhecidas(resto)

    return Intencao(
        termos=termos,
        estado=estado,
        cliente=cliente,
        responsavel=responsavel,
        so_atrasadas=so_atrasadas,
        perguntas=tuple(dict.fromkeys(perguntas)),  # sem repetições, ordem estável
        desconhecidas=desconhecidas,
    )


# ---- construção de mapas -------------------------------------------------
def _mapa_estados(perfil: PerfilVocabulario) -> dict[str, str]:
    mapa: dict[str, str] = {}
    for estado, formas in _ESTADOS_PADRAO.items():
        for forma in formas:
            mapa[forma] = estado
    # O perfil do utilizador tem prioridade sobre os defaults.
    for forma, estado in perfil.estados.items():
        forma_norm = normalizar(forma)
        if forma_norm:
            mapa[forma_norm] = estado
    return mapa


def _mapa_valores(
    valores: Iterable[str],
    aliases: Mapping[str, str],
) -> dict[str, str]:
    """Frase normalizada -> valor real (nome do próprio + alcunhas do perfil).

    Cada forma é registada também sem o artigo inicial, para «a Viva» apanhar
    «da Viva» na pergunta.
    """
    mapa: dict[str, str] = {}
    for valor in valores:
        for forma in _variantes_frase(normalizar(valor)):
            mapa[forma] = str(valor).strip()
    for alias, valor in aliases.items():
        for forma in _variantes_frase(normalizar(alias)):
            mapa[forma] = str(valor).strip()
    return mapa


def _variantes_frase(forma: str) -> tuple[str, ...]:
    """A frase e, se começar por artigo, a versão sem ele."""
    if not forma:
        return ()
    palavras = forma.split()
    if len(palavras) > 1 and palavras[0] in _ARTIGOS:
        return (forma, " ".join(palavras[1:]))
    return (forma,)


# ---- correspondência de frases ------------------------------------------
def _ordenar_por_tamanho(mapa: Mapping[str, str]):
    """Pares (forma, valor) das formas com mais palavras para as mais curtas."""
    itens = [(normalizar(forma), valor) for forma, valor in mapa.items()]
    itens = [(forma, valor) for forma, valor in itens if forma]
    return sorted(itens, key=lambda item: len(item[0].split()), reverse=True)


def _contem_frase(resto: str, forma: str) -> bool:
    return bool(forma) and f" {forma} " in resto


def _remover_frase(resto: str, forma: str) -> str:
    return resto.replace(f" {forma} ", " ") if forma else resto


def _extrair_frase(resto: str, mapa: Mapping[str, str]) -> tuple[str | None, str]:
    """Primeira frase do mapa presente no texto; devolve (valor, texto sem ela)."""
    for forma, valor in _ordenar_por_tamanho(mapa):
        if _contem_frase(resto, forma):
            return valor, _remover_frase(resto, forma)
    return None, resto


def _tem_alguma(resto: str, palavras: Iterable[str]) -> bool:
    return any(_contem_frase(resto, palavra) for palavra in palavras)


def _extrair_atraso(resto: str) -> tuple[bool, str]:
    palavras = resto.split()
    restantes = [p for p in palavras if raiz(p) not in _RAIZES_ATRASO]
    atrasadas = len(restantes) != len(palavras)
    return atrasadas, f" {' '.join(restantes)} "


def _extrair_possessivo(resto: str) -> tuple[bool, str]:
    palavras = resto.split()
    restantes = [p for p in palavras if raiz(p) not in _RAIZES_MINHAS]
    possessivo = len(restantes) != len(palavras)
    return possessivo, f" {' '.join(restantes)} "


def frase_resposta(intencao: Intencao, total: int) -> str:
    """Frase curta a dizer o que o martelo percebeu (Parte 4 do questionário)."""
    if total <= 0:
        return "Não encontrei obras para essa pergunta."

    obra = "obra" if total == 1 else "obras"
    partes = [f"Encontrei {total} {obra}"]
    if intencao.responsavel:
        partes.append(f"de {intencao.responsavel}")
    if intencao.cliente:
        partes.append(f"do cliente {intencao.cliente}")
    if intencao.estado:
        partes.append(f"em {intencao.estado}")
    if intencao.so_atrasadas:
        partes.append("em atraso")
    if intencao.termos:
        partes.append(f"com «{intencao.termos}»")
    return " ".join(partes) + "."


def sugestao_recrutamento(
    intencao: Intencao,
    total: int,
    vocabulario: Iterable[str] = (),
) -> str:
    """«Não conheço «X» — quer ensiná-la?» quando a palavra não existe mesmo.

    Só quando a consulta não devolveu nada E a palavra não está no vocabulário
    das obras (senão seria uma palavra real que apenas não teve resultados).
    """
    if total > 0:
        return ""
    conhecidas = set(vocabulario)
    for palavra in intencao.desconhecidas:
        if raiz(palavra) not in conhecidas:
            return (
                f"Não conheço «{palavra}». Quer acrescentá-la ao "
                "«Assistente — o meu perfil»?"
            )
    return ""


def _termos_e_desconhecidas(resto: str) -> tuple[str, tuple[str, ...]]:
    palavras = [p for p in resto.split() if p and p not in _VAZIAS]
    termos = " ".join(palavras)
    # Nesta fase, tudo o que sobra é procurado como texto livre; a marcação de
    # «palavra desconhecida» (para o «quer ensinar-me?») é decidida em runtime,
    # quando a consulta não devolver nada. Fica aqui a lista para essa fase.
    return termos, tuple(palavras)
