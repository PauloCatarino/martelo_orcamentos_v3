"""Vocabulário dos tickets de ocorrência: tipos, estados, gravidade e origem.

Módulo puro (sem Qt, sem BD) para que o PDF, o texto do Teams e os testes
possam classificar um ticket sem arrastar a interface atrás.

A ``familia`` de cada classificação é o que permite a análise do fim do ano:
distingue o que foi **erro nosso** do que foi pedido do cliente ou dano alheio.
Sem isso, contar ocorrências por obra não diz nada — uma obra com dez pedidos
adicionais é uma boa obra, uma com dois erros de produção não é.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Classificacao:
    """One entry of a closed vocabulary: key stored, label shown."""

    chave: str
    rotulo: str
    #: "erro" (falha nossa), "aviso" (externo/cliente), "ok", "neutro".
    familia: str


TIPOS: tuple[Classificacao, ...] = (
    Classificacao("pedido_adicional", "Pedido adicional", "neutro"),
    Classificacao("assistencia", "Assistência", "neutro"),
    Classificacao("erro_producao", "Erro de produção", "erro"),
    Classificacao("erro_preparacao", "Erro de preparação", "erro"),
    Classificacao("erro_medidas", "Erro de medidas", "erro"),
    Classificacao("pecas_em_falta", "Peças em falta", "erro"),
    Classificacao("falta_ferragens", "Falta de ferragens", "erro"),
    Classificacao("atraso_entrega", "Atraso na entrega", "erro"),
    Classificacao("pecas_danificadas_transporte", "Danificado no transporte", "aviso"),
    Classificacao("pecas_danificadas_cliente", "Danificado pelo cliente", "aviso"),
    Classificacao("reclamacao_cliente", "Reclamação do cliente", "aviso"),
    Classificacao("outro", "Outro", "neutro"),
)
TIPO_PADRAO = "outro"

ESTADOS: tuple[Classificacao, ...] = (
    Classificacao("aberto", "Aberto", "aviso"),
    Classificacao("em_curso", "Em curso", "aviso"),
    Classificacao("resolvido", "Resolvido", "ok"),
    Classificacao("anulado", "Anulado", "neutro"),
)
ESTADO_PADRAO = "aberto"
#: Estados que ainda pedem trabalho — é o filtro por omissão da lista.
ESTADOS_ABERTOS: tuple[str, ...] = ("aberto", "em_curso")

GRAVIDADES: tuple[Classificacao, ...] = (
    Classificacao("baixa", "Baixa", "neutro"),
    Classificacao("media", "Média", "aviso"),
    Classificacao("alta", "Alta", "erro"),
)
GRAVIDADE_PADRAO = "media"

ORIGENS: tuple[Classificacao, ...] = (
    Classificacao("cliente", "Cliente", "aviso"),
    Classificacao("interno", "Interno", "erro"),
    Classificacao("montagem", "Montagem", "aviso"),
    Classificacao("transporte", "Transporte", "aviso"),
)
ORIGEM_PADRAO = "cliente"


def _mapa(itens: tuple[Classificacao, ...]) -> dict[str, Classificacao]:
    return {item.chave: item for item in itens}


TIPOS_POR_CHAVE = _mapa(TIPOS)
ESTADOS_POR_CHAVE = _mapa(ESTADOS)
GRAVIDADES_POR_CHAVE = _mapa(GRAVIDADES)
ORIGENS_POR_CHAVE = _mapa(ORIGENS)


def _normalizar(
    valor: str | None, mapa: dict[str, Classificacao], padrao: str
) -> str:
    """Return a known key: unknown/empty values fall back to ``padrao``."""
    chave = (valor or "").strip().lower()
    return chave if chave in mapa else padrao


def normalizar_tipo(valor: str | None) -> str:
    """Return a valid tipo key (unknown values become 'outro')."""
    return _normalizar(valor, TIPOS_POR_CHAVE, TIPO_PADRAO)


def normalizar_estado(valor: str | None) -> str:
    """Return a valid estado key (unknown values become 'aberto')."""
    return _normalizar(valor, ESTADOS_POR_CHAVE, ESTADO_PADRAO)


def normalizar_gravidade(valor: str | None) -> str:
    """Return a valid gravidade key (unknown values become 'media')."""
    return _normalizar(valor, GRAVIDADES_POR_CHAVE, GRAVIDADE_PADRAO)


def normalizar_origem(valor: str | None) -> str:
    """Return a valid origem key (unknown values become 'cliente')."""
    return _normalizar(valor, ORIGENS_POR_CHAVE, ORIGEM_PADRAO)


def rotulo_tipo(valor: str | None) -> str:
    """Human label of a tipo key."""
    return TIPOS_POR_CHAVE[normalizar_tipo(valor)].rotulo


def rotulo_estado(valor: str | None) -> str:
    """Human label of an estado key."""
    return ESTADOS_POR_CHAVE[normalizar_estado(valor)].rotulo


def rotulo_gravidade(valor: str | None) -> str:
    """Human label of a gravidade key."""
    return GRAVIDADES_POR_CHAVE[normalizar_gravidade(valor)].rotulo


def rotulo_origem(valor: str | None) -> str:
    """Human label of an origem key."""
    return ORIGENS_POR_CHAVE[normalizar_origem(valor)].rotulo


def familia_tipo(valor: str | None) -> str:
    """Family of a tipo key: 'erro', 'aviso' or 'neutro'."""
    return TIPOS_POR_CHAVE[normalizar_tipo(valor)].familia


def familia_estado(valor: str | None) -> str:
    """Family of an estado key: drives the badge colour."""
    return ESTADOS_POR_CHAVE[normalizar_estado(valor)].familia


def e_erro_nosso(valor: str | None) -> bool:
    """True when this tipo counts as our own mistake (year-end analysis)."""
    return familia_tipo(valor) == "erro"


def esta_aberto(estado: str | None) -> bool:
    """True while the ticket still needs work."""
    return normalizar_estado(estado) in ESTADOS_ABERTOS


def rotulo_ticket(numero: int | None) -> str:
    """Return the short ticket reference: 7 -> 'T7'."""
    if not numero:
        return "T?"
    return f"T{int(numero)}"


def pasta_ticket(numero: int | None) -> str:
    """Return the ticket folder name: 7 -> 'T0007' (sorts right in Explorer)."""
    if not numero:
        return "T0000"
    return f"T{int(numero):04d}"
