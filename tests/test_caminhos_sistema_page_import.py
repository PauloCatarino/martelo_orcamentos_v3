"""Import checks for the CaminhosSistema page."""

from __future__ import annotations

import inspect


def test_caminhos_sistema_page_imports() -> None:
    from app.ui.pages.caminhos_sistema_page import CaminhosSistemaPage

    assert CaminhosSistemaPage is not None


def test_caminhos_sistema_page_loads_on_init() -> None:
    from app.ui.pages.caminhos_sistema_page import CaminhosSistemaPage

    source_names = CaminhosSistemaPage.__init__.__code__.co_names

    assert "carregar_configuracoes" in source_names
    assert "QTableWidget" in source_names


def test_caminhos_sistema_page_table_headers() -> None:
    from app.ui.pages.caminhos_sistema_page import CaminhosSistemaPage

    assert CaminhosSistemaPage.TABLE_HEADERS == [
        "Descri\u00e7\u00e3o / Campo",
        "Valor",
        "Procurar",
    ]


def test_caminhos_sistema_page_uses_service_for_load_and_save() -> None:
    from app.ui.pages.caminhos_sistema_page import CaminhosSistemaPage

    load_source = inspect.getsource(CaminhosSistemaPage.carregar_configuracoes)
    save_source = inspect.getsource(CaminhosSistemaPage.guardar_configuracoes)

    assert "SystemSettingService" in load_source
    assert "listar_configuracoes" in load_source
    assert "guardar_varios" in save_source


def test_caminhos_sistema_page_supports_browse_buttons() -> None:
    from app.ui.pages.caminhos_sistema_page import CaminhosSistemaPage

    source = inspect.getsource(CaminhosSistemaPage._procurar)

    assert "getExistingDirectory" in source
    assert "getOpenFileName" in source
    assert CaminhosSistemaPage.BROWSE_TYPES == {"pasta", "ficheiro"}
