"""Import checks for the Clientes page."""

from __future__ import annotations


def test_clientes_page_imports() -> None:
    from app.ui.pages.clientes_page import ClientesPage

    assert ClientesPage is not None


def test_separador_phc_sem_texto_desatualizado() -> None:
    import inspect
    from app.ui.pages.clientes_page import ClientesPage

    fonte = inspect.getsource(ClientesPage._criar_tab_phc)
    assert "fase futura" not in fonte
    assert "Atualizar PHC" in fonte
