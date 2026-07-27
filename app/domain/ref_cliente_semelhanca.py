"""Comparacao de Ref. Cliente: apanha o que esta igual e o que esta parecido.

A referencia do cliente e escrita a mao, por isso a mesma obra aparece escrita
de maneiras diferentes ao longo do tempo («REF-NOVO», «ref novo», «Ref. Novos»)
e o aviso de duplicado por igualdade exata deixa-a passar.

Comparar por «percentagem de caracteres em comum» resolveria esses casos mas
daria alarmes falsos nas referencias numericas do PHC, onde ``2512023`` e
``2512024`` sao obras diferentes e nao um erro de escrita. Por isso a
comparacao tem tres regras, da mais segura para a mais abrangente:

1. **Chave canonica** — minusculas, sem acentos, sem pontuacao nem espacos e
   com os plurais reduzidos a raiz (reaproveita :mod:`app.domain.pesquisa_texto`).
   Chaves iguais = referencia IGUAL.
2. **Contencao** — uma chave esta dentro da outra («refnovo» / «refnovo2»).
3. **Semelhanca com ordem** (:mod:`difflib`) acima de :data:`LIMIAR_PARECIDA`.
   Ao contrario da contagem de caracteres, «1234» e «4321» nao se parecem.

Salvaguarda das referencias numericas: quando as duas chaves sao so digitos,
vale apenas a regra 1 — um digito trocado e outra obra.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass

from app.domain.pesquisa_texto import raizes

#: A partir de que semelhanca (0..1) se avisa o utilizador.
LIMIAR_PARECIDA = 0.85

#: A chave mais curta nunca conta como «contida» abaixo deste tamanho, senao
#: um «ref» apanhava tudo.
_MINIMO_CONTENCAO = 4

#: E tambem nao conta quando e muito mais curta do que a outra.
_MINIMO_PROPORCAO_CONTENCAO = 0.6

IGUAL = "igual"
PARECIDA = "parecida"


@dataclass(frozen=True)
class Semelhanca:
    """Quao parecidas sao duas Ref. Cliente."""

    grau: str
    pontuacao: float

    @property
    def e_igual(self) -> bool:
        """True quando as duas referencias sao a mesma coisa escrita ao contrario."""
        return self.grau == IGUAL

    @property
    def etiqueta(self) -> str:
        """Texto curto para mostrar na tabela do aviso."""
        if self.e_igual:
            return "Igual"
        return f"Parecida ({round(self.pontuacao * 100)}%)"

    @property
    def explicacao(self) -> str:
        """Frase de ajuda (tooltip) para o utilizador decidir."""
        if self.e_igual:
            return (
                "Mesma referência, ignorando maiúsculas, acentos, "
                "espaços, pontuação e plurais."
            )
        return (
            "Referência parecida com a que escreveu — confirme se não "
            "é o mesmo orçamento escrito de outra maneira."
        )


def chave_ref(valor: object) -> str:
    """Forma canonica da referencia: sem acentos, sem pontuacao e sem plurais."""
    return "".join(raizes(valor))


def comparar(nova: object, existente: object) -> Semelhanca | None:
    """Compara duas Ref. Cliente; None quando nao ha motivo para avisar."""
    chave_nova = chave_ref(nova)
    chave_existente = chave_ref(existente)
    if not chave_nova or not chave_existente:
        return None

    if chave_nova == chave_existente:
        return Semelhanca(IGUAL, 1.0)

    if chave_nova.isdigit() and chave_existente.isdigit():
        # Referencias so com digitos: digitos diferentes sao obras diferentes.
        return None

    pontuacao = difflib.SequenceMatcher(None, chave_nova, chave_existente).ratio()
    if _uma_contem_a_outra(chave_nova, chave_existente) or pontuacao >= LIMIAR_PARECIDA:
        return Semelhanca(PARECIDA, pontuacao)

    return None


def _uma_contem_a_outra(chave_a: str, chave_b: str) -> bool:
    """True quando a chave mais curta esta dentro da mais longa (e conta)."""
    curta, longa = sorted((chave_a, chave_b), key=len)
    if len(curta) < _MINIMO_CONTENCAO:
        return False
    if len(curta) / len(longa) < _MINIMO_PROPORCAO_CONTENCAO:
        return False
    return curta in longa
