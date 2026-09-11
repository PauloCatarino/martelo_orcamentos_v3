"""Canonical budget status values."""

from __future__ import annotations

ESTADOS_ORCAMENTO: tuple[str, ...] = (
    "Falta Or\u00e7amentar",
    "Enviado",
    "Conclu\u00eddo",
    "N\u00e3o Enviado",
    "Adjudicado",
    "Sem Interesse",
    "N\u00e3o Adjudicado",
    "Cancelado",
)
ESTADO_INICIAL = "Falta Or\u00e7amentar"
ESTADO_ADJUDICADO = "Adjudicado"
ESTADO_ENVIADO = "Enviado"

#: Estados que significam "ainda nao foi para o cliente". So' a partir destes
#: e' que o envio do email faz o orcamento passar a Enviado.
ESTADOS_POR_ENVIAR: frozenset[str] = frozenset(
    {ESTADO_INICIAL, "N\u00e3o Enviado"}
)


def estado_apos_envio(estado_atual: str | None) -> str | None:
    """O estado a gravar depois de o or\u00e7amento seguir por email.

    Devolve ``None`` quando n\u00e3o h\u00e1 nada a mudar.

    S\u00f3 sobe de "Falta Or\u00e7amentar" ou "N\u00e3o Enviado" para
    "Enviado". Um or\u00e7amento j\u00e1 **Adjudicado** que se volte a enviar
    ao cliente n\u00e3o pode recuar para Enviado -- seria apagar a informa\u00e7\u00e3o
    de trabalho j\u00e1 ganho. O mesmo para Conclu\u00eddo, Cancelado ou Sem
    Interesse: se algu\u00e9m l\u00e1 p\u00f4s esse estado, foi de prop\u00f3sito.
    """
    if (estado_atual or "") in ESTADOS_POR_ENVIAR:
        return ESTADO_ENVIADO
    return None


def deve_avisar_cliente_phc(
    estado_anterior: str | None, novo_estado: str, cliente_temporario: bool
) -> bool:
    """True when a budget moves to Adjudicado with a temporary customer."""
    return (
        cliente_temporario
        and novo_estado == ESTADO_ADJUDICADO
        and (estado_anterior or "") != ESTADO_ADJUDICADO
    )


#: Estados em que a chegada de uma encomenda PHC NAO deve sugerir nada. Ou ja'
#: esta' adjudicado, ou alguem fechou o orcamento de proposito e quem manda e'
#: essa decisao -- a sugestao seria a pedir para a desfazer sem pensar.
ESTADOS_SEM_SUGESTAO_PHC: frozenset[str] = frozenset(
    {ESTADO_ADJUDICADO, "Cancelado", "Sem Interesse"}
)


def estado_apos_encomenda_phc(estado_atual: str | None) -> str | None:
    """O estado a SUGERIR quando se junta uma encomenda PHC ao orcamento.

    Devolve ``None`` quando nao ha' nada a sugerir.

    Uma encomenda PHC quer dizer que o cliente encomendou, ou seja, que o
    trabalho foi ganho -- mas o estado ficava no que estivesse ("Enviado", as
    mais das vezes) porque ninguem se lembrava de o mudar a` mao. Dai' a
    sugestao.

    **Sugerir, nunca decidir.** Quem mudou o estado para Cancelado ou Sem
    Interesse fe-lo de proposito; nesses casos o Martelo cala-se, em vez de
    convidar a desfazer uma decisao que alguem tomou. E em Adjudicado nao ha'
    nada a fazer.
    """
    if (estado_atual or "").strip() in ESTADOS_SEM_SUGESTAO_PHC:
        return None
    return ESTADO_ADJUDICADO
