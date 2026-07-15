from __future__ import annotations

import inspect


def test_arquivo_v2_page_expoe_edicao_partilhada():
    from app.ui.pages.arquivo_v2_page import ArquivoV2Page

    source = inspect.getsource(ArquivoV2Page)
    assert "Editar selecionado" in source
    assert "criar_engine_v2(read_only=False)" in source
    assert "atualizar_orcamento" in source


def test_main_window_expoe_arquivo_v2():
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)
    assert "Arquivo V2" in source
    assert "ArquivoV2Page" in source
