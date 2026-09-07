"""Preços escritos em parcelas: «0,25 + 0,15».

Pedido pelo Paulo a 07-09-2026. Uma ferragem é muitas vezes um conjunto — o
suporte TRIS são dois artigos, o pé AXILO são três — e o total é o que conta,
mas ver as parcelas deixa perceber de onde vem o preço.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.numeros import parcelas_do_preco, somar_parcelas, tem_parcelas


def test_um_preco_simples_e_uma_parcela_so() -> None:
    assert parcelas_do_preco("0,25") == [Decimal("0.25")]
    assert somar_parcelas("0,25") == Decimal("0.25")
    assert tem_parcelas("0,25") is False


def test_soma_de_duas_parcelas() -> None:
    assert parcelas_do_preco("0,25+0,15") == [Decimal("0.25"), Decimal("0.15")]
    assert somar_parcelas("0,25+0,15") == Decimal("0.40")
    assert tem_parcelas("0,25+0,15") is True


def test_espacos_e_euros_pelo_meio_nao_estorvam() -> None:
    assert somar_parcelas(" 0,25 € + 0,15 € + 0,02 € ") == Decimal("0.42")


def test_ponto_e_virgula_valem_o_mesmo() -> None:
    assert somar_parcelas("0.25+0,15") == Decimal("0.40")


def test_vazio_nao_e_preco_nenhum() -> None:
    assert parcelas_do_preco("") == []
    assert parcelas_do_preco(None) == []
    assert somar_parcelas("   ") is None
    assert tem_parcelas("") is False


def test_uma_parcela_a_meio_do_ar_e_erro() -> None:
    # "0,25+" e' meio caminho de escrever: nao pode passar por 0,25.
    for escrito in ("0,25+", "+0,15", "0,25++0,15", "0,25 + abc"):
        with pytest.raises(ValueError):
            parcelas_do_preco(escrito)


def test_muitas_parcelas() -> None:
    assert somar_parcelas("1+2+3+4+5") == Decimal("15")


def test_o_total_nao_perde_casas_decimais() -> None:
    # Decimal, nao float: 0,1 + 0,2 tem de dar 0,3 exacto.
    assert somar_parcelas("0,1+0,2") == Decimal("0.3")
