"""Escrever euros por extenso, em português de Portugal."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.numero_extenso import euros_por_extenso, inteiro_por_extenso


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [
        (0, "zero"),
        (1, "um"),
        (14, "catorze"),          # e não "quatorze"
        (16, "dezasseis"),        # e não "dezesseis"
        (17, "dezassete"),
        (19, "dezanove"),
        (20, "vinte"),
        (21, "vinte e um"),
        (100, "cem"),             # sozinho é "cem"
        (101, "cento e um"),      # acompanhado é "cento"
        (200, "duzentos"),
        (236, "duzentos e trinta e seis"),
        (999, "novecentos e noventa e nove"),
    ],
)
def test_ate_mil(numero: int, esperado: str) -> None:
    assert inteiro_por_extenso(numero) == esperado


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [
        (1000, "mil"),                     # "mil", não "um mil"
        (1001, "mil e um"),
        (1059, "mil e cinquenta e nove"),
        (1200, "mil e duzentos"),          # centena redonda leva "e"
        (1230, "mil duzentos e trinta"),   # e esta não leva
        (2000, "dois mil"),
        (236059, "duzentos e trinta e seis mil e cinquenta e nove"),
    ],
)
def test_os_milhares_e_o_e(numero: int, esperado: str) -> None:
    assert inteiro_por_extenso(numero) == esperado


@pytest.mark.parametrize(
    ("numero", "esperado"),
    [
        (1_000_000, "um milhão"),
        (2_000_000, "dois milhões"),
        (1_000_030, "um milhão e trinta"),
        (2_500_000, "dois milhões e quinhentos mil"),
        (
            1_234_567,
            "um milhão duzentos e trinta e quatro mil quinhentos e sessenta e sete",
        ),
    ],
)
def test_os_milhoes(numero: int, esperado: str) -> None:
    assert inteiro_por_extenso(numero) == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        ("0.00", "zero euros"),
        ("1.00", "um euro"),
        ("2.00", "dois euros"),
        ("0.01", "um cêntimo"),
        ("0.50", "cinquenta cêntimos"),
        ("1.01", "um euro e um cêntimo"),
        (
            "236059.86",
            "duzentos e trinta e seis mil e cinquenta e nove euros e "
            "oitenta e seis cêntimos",
        ),
        ("-45.50", "menos quarenta e cinco euros e cinquenta cêntimos"),
    ],
)
def test_euros(valor: str, esperado: str) -> None:
    assert euros_por_extenso(valor) == esperado


def test_aceita_decimal_e_float() -> None:
    assert euros_por_extenso(Decimal("12.30")) == "doze euros e trinta cêntimos"
    assert euros_por_extenso(12.3) == "doze euros e trinta cêntimos"


def test_arredonda_aos_centimos() -> None:
    assert euros_por_extenso("1.005") == "um euro e um cêntimo"


def test_o_que_nao_e_numero_devolve_vazio() -> None:
    assert euros_por_extenso(None) == ""
    assert euros_por_extenso("abc") == ""
