"""Escrever um valor em euros por extenso, em português de Portugal.

Serve o rodapé da lista de orçamentos: um total como ``236 059,86 €`` lê-se mal
de relance — é fácil trocar duzentos e trinta e seis mil por vinte e três mil.
Escrito também por extenso, não há dúvida nenhuma.

Regras de pt-PT que o código respeita, e que são o que costuma sair mal:

- ``catorze``, ``dezasseis``, ``dezassete``, ``dezanove`` (e não as formas do
  Brasil).
- ``cem`` sozinho, ``cento e ...`` quando leva mais alguma coisa.
- O ``e`` antes do último grupo só entra quando esse grupo é menor que cem ou
  uma centena redonda: ``mil e cinquenta e nove``, ``mil e duzentos``, mas
  ``mil duzentos e trinta``.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

_ATE_VINTE = (
    "zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito",
    "nove", "dez", "onze", "doze", "treze", "catorze", "quinze", "dezasseis",
    "dezassete", "dezoito", "dezanove",
)
_DEZENAS = (
    "", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta",
    "oitenta", "noventa",
)
_CENTENAS = (
    "", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
    "seiscentos", "setecentos", "oitocentos", "novecentos",
)

#: (singular, plural) de cada escala, da maior para a menor.
_ESCALAS = ((10**9, "mil milhões", "mil milhões"), (10**6, "milhão", "milhões"))


def _ate_999(numero: int) -> str:
    """Escrever um número de 1 a 999."""
    if numero < 20:
        return _ATE_VINTE[numero]
    if numero < 100:
        dezena, unidade = divmod(numero, 10)
        texto = _DEZENAS[dezena]
        return f"{texto} e {_ATE_VINTE[unidade]}" if unidade else texto
    if numero == 100:
        return "cem"
    centena, resto = divmod(numero, 100)
    texto = _CENTENAS[centena]
    return f"{texto} e {_ate_999(resto)}" if resto else texto


def _ligar(principal: str, resto: int) -> str:
    """Juntar o resto ao que já está escrito, com ou sem "e"."""
    if not resto:
        return principal
    # "mil e cinquenta e nove", "mil e duzentos", mas "mil duzentos e trinta".
    separador = " e " if resto < 100 or resto % 100 == 0 else " "
    return f"{principal}{separador}{_ate_999(resto)}"


def inteiro_por_extenso(numero: int) -> str:
    """Escrever um inteiro não negativo por extenso."""
    numero = int(numero)
    if numero < 0:
        return f"menos {inteiro_por_extenso(-numero)}"
    if numero < 1000:
        return _ate_999(numero)

    for valor, singular, plural in _ESCALAS:
        if numero >= valor:
            quantos, resto = divmod(numero, valor)
            nome = singular if quantos == 1 else plural
            cabeca = f"{inteiro_por_extenso(quantos)} {nome}"
            if not resto:
                return cabeca
            # "e" quando o que sobra é uma parcela só: "um milhão e trinta",
            # "dois milhões e quinhentos mil" — mas "um milhão duzentos e
            # trinta e quatro mil quinhentos e sessenta e sete".
            separador = " e " if resto < 1000 or resto % 1000 == 0 else " "
            return f"{cabeca}{separador}{inteiro_por_extenso(resto)}"

    milhares, resto = divmod(numero, 1000)
    cabeca = "mil" if milhares == 1 else f"{_ate_999(milhares)} mil"
    return _ligar(cabeca, resto)


def euros_por_extenso(valor) -> str:
    """Escrever um valor em euros por extenso (com os cêntimos).

    Devolve "" quando o valor não é um número. Arredonda aos cêntimos da mesma
    maneira que o resto do programa (meia unidade para cima).
    """
    try:
        montante = Decimal(str(valor)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    except (ArithmeticError, TypeError, ValueError):
        return ""

    negativo = montante < 0
    montante = abs(montante)
    inteiros = int(montante)
    centimos = int((montante - inteiros) * 100)

    partes = []
    if inteiros or not centimos:
        moeda = "euro" if inteiros == 1 else "euros"
        partes.append(f"{inteiro_por_extenso(inteiros)} {moeda}")
    if centimos:
        unidade = "cêntimo" if centimos == 1 else "cêntimos"
        partes.append(f"{inteiro_por_extenso(centimos)} {unidade}")

    texto = " e ".join(partes)
    return f"menos {texto}" if negativo else texto
