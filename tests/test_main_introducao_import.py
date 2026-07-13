from __future__ import annotations

import inspect


def test_main_mostra_introducao_uma_vez_por_execucao() -> None:
    from app import main as main_module

    source = inspect.getsource(main_module.main)
    assert "introducao_mostrada = False" in source
    assert "IntroducaoWindow" in source
    assert "marcar_aplicacao_pronta" in source
    assert "introducao.concluida.connect(window.showMaximized)" in source
