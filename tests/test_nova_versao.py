"""Um numero novo para cada instalador que sai.

O numero da versao e' a unica forma de saber o que e' que cada colega tem
instalado. Estes testes fixam as duas coisas que o protegem: subir sempre, e
nunca deixar sair dois instaladores diferentes com o mesmo nome.
"""

from __future__ import annotations

import pytest

from scripts.nova_versao import (
    aplicar,
    e_maior,
    ler_versao,
    proxima_versao,
    validar,
)

FONTE = '''"""Versao do Martelo."""

APP_VERSION = "1.0.0"

APP_STAGE = ""
'''


def test_le_a_versao_que_esta_no_ficheiro() -> None:
    assert ler_versao(FONTE) == "1.0.0"


def test_ficheiro_sem_a_linha_diz_o_que_se_passa() -> None:
    with pytest.raises(ValueError, match="APP_VERSION"):
        ler_versao('APP_STAGE = ""')


@pytest.mark.parametrize(
    ("atual", "esperado"),
    [
        ("1.0.0", "1.0.1"),
        ("1.0.9", "1.0.10"),
        ("1.2.3", "1.2.4"),
        ("0.9.9", "0.9.10"),
    ],
)
def test_sobe_o_ultimo_numero(atual: str, esperado: str) -> None:
    assert proxima_versao(atual) == esperado


def test_aplicar_troca_so_a_linha_da_versao() -> None:
    novo = aplicar(FONTE, "1.0.1")
    assert 'APP_VERSION = "1.0.1"' in novo
    assert 'APP_VERSION = "1.0.0"' not in novo
    # O resto do ficheiro fica intacto -- o APP_STAGE decide se e' oficial.
    assert 'APP_STAGE = ""' in novo


@pytest.mark.parametrize("mau", ["1.0", "v1.0.0", "1.0.0-beta", "", "abc"])
def test_recusa_numeros_que_nao_servem(mau: str) -> None:
    with pytest.raises(ValueError):
        validar(mau)


def test_aceita_numero_bem_escrito() -> None:
    assert validar("2.10.3") == "2.10.3"


@pytest.mark.parametrize(
    ("nova", "atual", "sobe"),
    [
        ("1.0.1", "1.0.0", True),
        ("1.1.0", "1.0.9", True),
        ("2.0.0", "1.9.9", True),
        ("1.0.10", "1.0.9", True),   # 10 e' maior que 9, nao alfabetico
        ("1.0.0", "1.0.0", False),   # repetir e' o erro que isto evita
        ("1.0.2", "1.0.5", False),   # descer sem dar por isso
    ],
)
def test_uma_versao_nova_tem_de_subir(nova: str, atual: str, sobe: bool) -> None:
    assert e_maior(nova, atual) is sobe
