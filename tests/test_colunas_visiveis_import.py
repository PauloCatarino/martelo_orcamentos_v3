"""Import and pure-function tests for visible-column helper."""

from __future__ import annotations


def test_helper_importa() -> None:
    from app.ui.widgets.colunas_visiveis import (
        estado_inicial_colunas,
        ligar_menu_colunas,
    )

    assert callable(estado_inicial_colunas)
    assert callable(ligar_menu_colunas)


def test_estado_inicial_aplica_default_sem_guardados() -> None:
    from app.ui.widgets.colunas_visiveis import estado_inicial_colunas

    estados = estado_inicial_colunas(
        ["C\u00f3digo", "Descri\u00e7\u00e3o", "Custo total"],
        {},
        {"C\u00f3digo", "Descri\u00e7\u00e3o"},
    )

    assert estados == {0: False, 1: False, 2: True}


def test_estado_inicial_guardado_vence_default() -> None:
    from app.ui.widgets.colunas_visiveis import estado_inicial_colunas

    estados = estado_inicial_colunas(
        ["C\u00f3digo", "Descri\u00e7\u00e3o", "Custo total"],
        {0: True, 2: False},
        {"C\u00f3digo"},
    )

    assert estados == {0: True, 1: True, 2: False}


def test_estado_inicial_repor_padrao_sem_guardados() -> None:
    from app.ui.widgets.colunas_visiveis import estado_inicial_colunas

    guardados = {0: True, 1: True}
    assert estado_inicial_colunas(["C\u00f3digo", "Descri\u00e7\u00e3o"], guardados, {"C\u00f3digo"}) == {
        0: True,
        1: True,
    }

    estados_repostos = estado_inicial_colunas(
        ["C\u00f3digo", "Descri\u00e7\u00e3o"],
        {},
        {"C\u00f3digo"},
    )

    assert estados_repostos == {0: False, 1: True}


def test_estado_inicial_nao_esconde_todas() -> None:
    from app.ui.widgets.colunas_visiveis import estado_inicial_colunas

    estados = estado_inicial_colunas(["A", "B"], {0: False, 1: False}, set())

    assert estados == {0: True, 1: False}
