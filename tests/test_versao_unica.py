"""Há um número de versão só — o do instalador é o do diário de bordo.

Andavam dois: o `version.py` da raiz (instalador) ia na 0.9.6-beta enquanto o
`app/config/versao.py` (diário de bordo e "Reportar problema") ficara na 3.2.0.
Quem reportasse um problema dizia um número que não correspondia ao instalador
que tinha à frente.
"""

from __future__ import annotations

import re

from app.config.versao import APP_STAGE, APP_VERSION, VERSAO_APLICACAO
from app.config.versao import version_completa as versao_da_app
from version import version_completa as versao_do_instalador


def test_o_instalador_e_o_diario_dizem_o_mesmo() -> None:
    assert versao_do_instalador() == versao_da_app()


def test_o_que_o_utilizador_ve_e_a_versao_completa() -> None:
    # É este o número que aparece no "Reportar problema".
    assert VERSAO_APLICACAO == versao_da_app()
    assert VERSAO_APLICACAO.startswith(APP_VERSION)


def test_o_formato_do_numero_e_o_esperado() -> None:
    # x.y.z, com o estado colado por um hífen quando existe.
    assert re.fullmatch(r"\d+\.\d+\.\d+", APP_VERSION)
    if APP_STAGE:
        assert versao_da_app() == f"{APP_VERSION}-{APP_STAGE}"
    else:
        assert versao_da_app() == APP_VERSION


def test_o_numero_vive_no_pacote_da_aplicacao() -> None:
    """A raiz só reexporta: assim o executável encontra-o pelo caminho da app.

    Se um dia alguém voltar a escrever o número no `version.py` da raiz, os
    dois separam-se outra vez — e este teste deixa de o apanhar.
    """
    import inspect

    import version

    fonte = inspect.getsource(version)

    assert "from app.config.versao import" in fonte
    assert "APP_VERSION = " not in fonte
