from __future__ import annotations

import inspect


def test_arquivo_v2_page_e_apenas_leitura() -> None:
    from app.ui.pages.arquivo_v2_page import ArquivoV2Page

    source = inspect.getsource(ArquivoV2Page.carregar)
    assert "criar_engine_v2_readonly" in source
    assert "V2ArquivoService" in source
    assert "engine.dispose" in source


def test_main_window_expoe_arquivo_v2() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)
    assert "Arquivo V2" in source
    assert "ArquivoV2Page" in source
