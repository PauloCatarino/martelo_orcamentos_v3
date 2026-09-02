"""Canonical production status values."""

from __future__ import annotations

import unicodedata

ESTADOS_PRODUCAO: tuple[str, ...] = (
    "Desenho",
    "Producao",
    "Finalizado",
    "Arquivado",
)

ESTADO_DESENHO = "Desenho"
ESTADO_PRODUCAO = "Producao"

#: Estados que sao do UTILIZADOR: e' ele que os marca no Martelo quando poe a
#: obra a desenhar ou a produzir. Nunca vem de fora -- se o PHC os copiasse
#: para ca', apagava a decisao de quem esta' a trabalhar na obra.
ESTADOS_DO_UTILIZADOR: tuple[str, ...] = (ESTADO_DESENHO, ESTADO_PRODUCAO)

#: Estados que vem SEMPRE de fora: quem fecha ou arquiva uma obra sao outras
#: pessoas da empresa, no PHC (encomendas de cliente) ou no Streamlit (cliente
#: final). No Martelo ninguem os escolhe a` mao -- so' se aceitam de la'.
ESTADOS_EXTERNOS: tuple[str, ...] = ("Finalizado", "Arquivado")


def _normalizar(estado: object) -> str:
    """Compare states without caring about accents or capitals.

    Em obras antigas (e no que vem do PHC/Streamlit) aparece "Produção" com
    acento, por isso não se pode comparar o texto em bruto.
    """
    texto = unicodedata.normalize("NFKD", str(estado or "").strip())
    return "".join(c for c in texto if not unicodedata.combining(c)).casefold()


#: A vida de uma obra so' anda para a frente: Desenho, Producao, Finalizado,
#: Arquivado. Serve para recusar uma sugestao que a fizesse recuar -- ja' se
#: viu o PHC a querer por uma obra arquivada de volta em producao.
_ORDEM_DA_VIDA: dict[str, int] = {
    _normalizar(estado): posicao
    for posicao, estado in enumerate(ESTADOS_PRODUCAO)
}


def vem_de_fora(estado: object) -> bool:
    """True quando este estado e' atribuido no PHC/Streamlit, nao no Martelo."""
    return _normalizar(estado) in {_normalizar(e) for e in ESTADOS_EXTERNOS}


def avanca_na_vida_da_obra(atual: object, novo: object) -> bool:
    """True quando ``novo`` esta' a` frente de ``atual`` na vida da obra.

    Um estado que o Martelo nao conhece conta como o principio de tudo: uma
    obra sem estado escrito pode receber qualquer um dos outros.
    """
    posicao_atual = _ORDEM_DA_VIDA.get(_normalizar(atual), -1)
    posicao_nova = _ORDEM_DA_VIDA.get(_normalizar(novo), -1)
    if posicao_nova < 0:
        return False
    return posicao_nova > posicao_atual


def e_producao(estado: object) -> bool:
    """True when this state means the obra is in production."""
    return _normalizar(estado) == _normalizar(ESTADO_PRODUCAO)


def entra_em_producao(estado_anterior: object, estado_novo: object) -> bool:
    """True when the obra is moving into production from another state."""
    return e_producao(estado_novo) and not e_producao(estado_anterior)
