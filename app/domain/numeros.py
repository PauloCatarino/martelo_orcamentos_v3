"""Helpers for parsing and normalizing human numbers and percentages."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation


def parse_decimal_humano(texto: str | None) -> Decimal | None:
    """Parse a human decimal string into a Decimal.

    Accepts comma or dot as the decimal separator and ignores spaces, the euro
    sign and the percent sign. Returns None for empty input and raises
    ValueError for invalid input.

    Examples: "8,62" -> 8.62, "0,1" -> 0.1, "10,5" -> 10.5.
    """
    if texto is None:
        return None

    normalized = (
        texto.strip()
        .replace(" ", "")
        .replace("€", "")
        .replace("%", "")
        .replace(",", ".")
    )
    if not normalized:
        return None

    try:
        numero = Decimal(normalized)
        if not numero.is_finite():
            raise ValueError("numero invalido")
        return numero
    except InvalidOperation as error:
        raise ValueError("numero invalido") from error


def validar_decimal(
    valor,
    campo: str,
    *,
    permitir_vazio: bool = True,
    minimo: Decimal | None = None,
    minimo_exclusivo: bool = False,
) -> Decimal | None:
    """Validate a finite decimal and an optional lower bound."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if permitir_vazio:
            return None
        raise ValueError(f"{campo} é obrigatório.")
    if isinstance(valor, bool):
        raise ValueError(f"{campo} inválido: introduza um número.")

    if isinstance(valor, Decimal):
        numero = valor
    elif isinstance(valor, (int, float)):
        try:
            numero = Decimal(str(valor))
        except InvalidOperation as error:
            raise ValueError(f"{campo} inválido: introduza um número.") from error
    elif isinstance(valor, str):
        try:
            numero = parse_decimal_humano(valor)
        except ValueError as error:
            raise ValueError(f"{campo} inválido: introduza um número.") from error
        if numero is None:
            if permitir_vazio:
                return None
            raise ValueError(f"{campo} é obrigatório.")
    else:
        raise ValueError(f"{campo} inválido: introduza um número.")

    if not numero.is_finite():
        raise ValueError(f"{campo} inválido: o valor tem de ser finito.")
    if minimo is not None:
        fora = numero <= minimo if minimo_exclusivo else numero < minimo
        if fora:
            comparacao = "maior que" if minimo_exclusivo else "maior ou igual a"
            raise ValueError(f"{campo} inválido: o valor tem de ser {comparacao} {minimo}.")
    return numero


def formatar_percentagem(valor: Decimal | None) -> str:
    """Format a human percentage for display, dropping needless decimals.

    Examples: None -> "", 10 -> "10%", 10.0 -> "10%", 6.8 -> "6.8%",
    12.50 -> "12.5%".
    """
    if valor is None:
        return ""

    return f"{format(valor.normalize(), 'f')}%"


def normalize_percentagem_humana(value: Decimal | None) -> Decimal | None:
    """Normalize an imported percentage into a human percentage.

    Values strictly between -1 and 1 are treated as fractions and multiplied by
    100 (0.1 -> 10, 0.32 -> 32). Values with magnitude >= 1 are assumed to be
    already in human percentage and kept as-is (5 -> 5, 36 -> 36).
    """
    if value is None:
        return None

    if Decimal(-1) < value < Decimal(1):
        return value * Decimal(100)

    return value


#: Uma ferragem é muitas vezes um conjunto de peças com preços diferentes — o
#: suporte TRIS são dois artigos, o pé AXILO são três. O total é o que conta
#: para as contas, mas escrever as parcelas deixa perceber de onde vem.
SEPARADOR_PARCELAS = "+"


def parcelas_do_preco(texto: str | None) -> list[Decimal]:
    """As parcelas escritas num preço, pela ordem em que aparecem.

    ``"0,25 + 0,15"`` dá ``[0.25, 0.15]``; um preço simples dá uma parcela só.
    Levanta ``ValueError`` quando alguma parcela não é um número — a mesma
    regra do ``parse_decimal_humano``, para o erro no ecrã ser o mesmo.
    """
    if texto is None:
        return []

    limpo = texto.strip()
    if not limpo:
        return []

    partes = [p for p in limpo.split(SEPARADOR_PARCELAS)]
    if any(not p.strip() for p in partes):
        # "0,25+" ou "+0,25": falta uma parcela, não é um preço escrito.
        raise ValueError("parcela vazia")

    numeros: list[Decimal] = []
    for parte in partes:
        numero = parse_decimal_humano(parte)
        if numero is None:
            raise ValueError("parcela vazia")
        numeros.append(numero)
    return numeros


def somar_parcelas(texto: str | None) -> Decimal | None:
    """O total de um preço escrito em parcelas, ou ``None`` se estiver vazio."""
    numeros = parcelas_do_preco(texto)
    if not numeros:
        return None
    return sum(numeros, Decimal(0))


def tem_parcelas(texto: str | None) -> bool:
    """Se o preço foi escrito como uma soma e não como um número só."""
    return len(parcelas_do_preco(texto)) > 1
