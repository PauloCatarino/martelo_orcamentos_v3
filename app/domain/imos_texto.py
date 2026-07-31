"""Texto livre que vai para o iMos: o que se troca e o que se avisa.

O Paulo apanhou uma encomenda com ``PUXADOR 'J' H1030`` na Descrição produção:
a **plica** (`'`) não é aceite do lado do iMos. Como a plica e as aspas dizem a
mesma coisa neste contexto, o Martelo troca-a sozinho por `"` — ninguém tem de
reescrever a descrição.

Para o resto não há lista oficial de caracteres proibidos, por isso aqui **não
se bloqueia nada**: o que sai do costume é assinalado no diálogo para o
utilizador ver antes de gravar. Preferimos avisar de mais a deixar passar uma
encomenda que o iMos depois não abre.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

#: Trocas automáticas: à esquerda o que o iMos não quer, à direita o
#: equivalente que diz o mesmo. As aspas "bonitas" e os traços longos entram
#: aqui porque aparecem sempre que se cola texto do Word ou do Excel.
SUBSTITUICOES: dict[str, str] = {
    "'": '"',
    "‘": '"',  # ‘
    "’": '"',  # ’
    "‚": '"',  # ‚
    "′": '"',  # ′
    "`": '"',  # `
    "´": '"',  # ´
    "“": '"',  # “
    "”": '"',  # ”
    "„": '"',  # „
    "–": "-",  # –
    "—": "-",  # —
    "‑": "-",  # ‑
    "…": "...",  # …
    " ": " ",  # espaço não separável (vem de colar do Word/Excel)
    "\t": " ",
}

#: Além de letras e algarismos (acentos incluídos), estes são os sinais que já
#: vimos em encomendas reais e damos por seguros.
PONTUACAO_SEGURA = ' .,;:-_/()+=%&#@!?*"ºª\n'


@dataclass(frozen=True)
class TextoImos:
    """Resultado da limpeza de um texto que vai ser gravado no iMos."""

    original: str
    valor: str
    #: Caracteres trocados automaticamente (já sem repetições).
    substituidos: tuple[str, ...] = ()
    #: Caracteres que ficaram e podem não ser aceites — só aviso.
    suspeitos: tuple[str, ...] = ()

    @property
    def mudou(self) -> bool:
        return self.valor != self.original

    @property
    def aviso(self) -> str:
        """Frase curta para a coluna 'Aviso' do diálogo (vazia se não há nada)."""
        partes = []
        if self.substituidos:
            trocados = " ".join(self.substituidos)
            partes.append(f"{trocados} trocado por aspas/traço")
        if self.suspeitos:
            partes.append(
                "caracteres invulgares: " + " ".join(self.suspeitos) + " — confirme"
            )
        return "; ".join(partes)


def limpar_texto_imos(valor: object) -> TextoImos:
    """Trocar o que o iMos não aceita e assinalar o que é invulgar."""
    original = str(valor or "")

    substituidos: list[str] = []
    letras: list[str] = []
    for caracter in original:
        troca = SUBSTITUICOES.get(caracter)
        if troca is not None:
            if caracter not in substituidos:
                substituidos.append(caracter)
            letras.append(troca)
            continue
        letras.append(caracter)
    limpo = "".join(letras)

    suspeitos: list[str] = []
    for caracter in limpo:
        if caracter.isalnum() or caracter in PONTUACAO_SEGURA:
            continue
        if caracter not in suspeitos:
            suspeitos.append(caracter)

    return TextoImos(
        original=original,
        valor=limpo,
        substituidos=tuple(substituidos),
        suspeitos=tuple(_legivel(c) for c in suspeitos),
    )


def _legivel(caracter: str) -> str:
    """Mostrar o caracter de forma reconhecível, mesmo quando é invisível."""
    if caracter.isprintable() and not caracter.isspace():
        return caracter
    nome = unicodedata.name(caracter, "")
    return f"[{nome or hex(ord(caracter))}]"
