"""Tests for the per-line quantity computation (phase 8T.4)."""

from __future__ import annotations

from decimal import Decimal

from app.domain.custeio_linha_types import (
    DIVISAO_INDEPENDENTE,
    FERRAGEM,
    PECA,
    PECA_COMPOSTA,
)
from app.domain.quantidades import (
    LinhaQuantidade,
    calcular_quantidades,
    formatar_cadeia,
)


def _div(id, qt_mod):
    return LinhaQuantidade(id=id, tipo_linha=DIVISAO_INDEPENDENTE, qt_mod=qt_mod)


def _peca(id, qt_und, qt_mod=Decimal("1"), tipo=PECA, linha_pai_id=None):
    return LinhaQuantidade(
        id=id,
        tipo_linha=tipo,
        qt_mod=qt_mod,
        qt_und=qt_und,
        linha_pai_id=linha_pai_id,
    )


def test_qt_total_peca_simples_num_bloco_divisao() -> None:
    # Division 1: the line below it is "1 x 1".
    linhas = [_div(1, Decimal("1")), _peca(2, Decimal("1"))]
    res = calcular_quantidades(linhas)

    assert res[2].qt_total == Decimal("1")
    assert res[2].cadeia == (Decimal("1"), Decimal("1"))

    # Division 3: the same line becomes "3 x 1" = 3.
    linhas = [_div(1, Decimal("3")), _peca(2, Decimal("1"))]
    res = calcular_quantidades(linhas)

    assert res[2].qt_total == Decimal("3")
    assert res[2].cadeia == (Decimal("3"), Decimal("1"))


def test_qt_total_componente_de_composta() -> None:
    # 1 module x 1 door x 5 hinges -> 5 ("1 x 1 x 5").
    linhas = [
        _div(1, Decimal("1")),
        _peca(2, Decimal("1"), tipo=PECA_COMPOSTA),  # main composite line
        _peca(3, Decimal("5"), tipo=FERRAGEM, linha_pai_id=2),  # 5 hinges
    ]
    res = calcular_quantidades(linhas)

    assert res[3].qt_total == Decimal("5")
    assert formatar_cadeia(res[3].cadeia) == "1 x 1 x 5"

    # Division 3 -> "3 x 1 x 5" = 15.
    linhas[0] = _div(1, Decimal("3"))
    res = calcular_quantidades(linhas)

    assert res[3].qt_total == Decimal("15")
    assert formatar_cadeia(res[3].cadeia) == "3 x 1 x 5"


def test_qt_total_componente_multiplica_qt_und_principal() -> None:
    # Main composite piece with qt_und 2 (two doors) x 5 hinges each = 10.
    linhas = [
        _peca(1, Decimal("2"), tipo=PECA_COMPOSTA),
        _peca(2, Decimal("5"), tipo=FERRAGEM, linha_pai_id=1),
    ]
    res = calcular_quantidades(linhas)

    # No division above: qt_mod_efetivo is the line's own qt_mod (1).
    assert res[2].qt_total == Decimal("10")  # 1 x 2 x 5
    assert res[2].cadeia == (Decimal("1"), Decimal("2"), Decimal("5"))


def test_divisao_governa_o_bloco_e_para_na_proxima_divisao() -> None:
    linhas = [
        _peca(1, Decimal("1"), qt_mod=Decimal("2")),  # above any division
        _div(2, Decimal("3")),
        _peca(3, Decimal("2")),  # block A: 3 x 2
        _div(4, Decimal("5")),
        _peca(5, Decimal("1")),  # block B: 5 x 1
    ]
    res = calcular_quantidades(linhas)

    assert res[1].qt_total == Decimal("2")  # own qt_mod (no division above)
    assert res[2].qt_total == Decimal("3")  # division module count
    assert res[3].qt_total == Decimal("6")  # 3 x 2
    assert res[4].qt_total == Decimal("5")
    assert res[5].qt_total == Decimal("5")  # 5 x 1 (new block)


def test_qt_mod_proprio_quando_sem_divisao_acima() -> None:
    linhas = [_peca(1, Decimal("4"), qt_mod=Decimal("3"))]
    res = calcular_quantidades(linhas)

    assert res[1].qt_total == Decimal("12")  # 3 x 4
    assert res[1].cadeia == (Decimal("3"), Decimal("4"))


def test_valores_em_falta_contam_como_um() -> None:
    linhas = [_peca(1, None, qt_mod=None)]
    res = calcular_quantidades(linhas)

    assert res[1].qt_total == Decimal("1")
    assert res[1].cadeia == (Decimal("1"), Decimal("1"))


def test_formatar_cadeia() -> None:
    assert formatar_cadeia((Decimal("1"), Decimal("1"), Decimal("5"))) == "1 x 1 x 5"
    assert formatar_cadeia((Decimal("3"), Decimal("1"), Decimal("5"))) == "3 x 1 x 5"
    assert formatar_cadeia((Decimal("3"),)) == "3"
    # Trailing zeros trimmed, comma decimals.
    assert formatar_cadeia((Decimal("1.50"), Decimal("2"))) == "1,5 x 2"
