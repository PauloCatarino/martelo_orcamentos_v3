from __future__ import annotations

import inspect


def test_pagina_importa_e_apresenta_impacto_financeiro() -> None:
    from app.ui.pages.custeio_auditoria_page import CusteioAuditoriaPage

    assert "Impacto financeiro" in CusteioAuditoriaPage.TABLE_HEADERS
    source = inspect.getsource(CusteioAuditoriaPage.carregar)
    assert "CusteioAuditoriaService" in source
    assert "impacto_conhecido" in source


def test_main_window_expoe_auditoria_de_custeio() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)
    assert "Auditoria de Custeio" in source
    assert "CusteioAuditoriaPage" in source


def test_auditoria_filtra_por_utilizador_autenticado() -> None:
    from app.ui.pages.custeio_auditoria_page import CusteioAuditoriaPage

    init = inspect.getsource(CusteioAuditoriaPage.__init__)
    carregar = inspect.getsource(CusteioAuditoriaPage.carregar)
    filtros = inspect.getsource(CusteioAuditoriaPage._aplicar_filtros)
    assert "utilizador_combo" in init
    assert "app_session.current_user" in carregar
    assert "item.utilizador == utilizador" in filtros


def test_auditoria_mostra_saude_e_navegacao_exata() -> None:
    from app.ui.pages.custeio_auditoria_page import CusteioAuditoriaPage
    from app.ui.pages.orcamento_detail_page import OrcamentoDetailPage
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(CusteioAuditoriaPage, "_preencher_saude")
    assert hasattr(OrcamentoDetailPage, "abrir_item_custeio_por_id")
    assert hasattr(OrcamentoItemCusteioPage, "selecionar_linha_por_id")


def test_pagina_explica_que_saude_inclui_observacoes_producao() -> None:
    from app.ui.pages.custeio_auditoria_page import CusteioAuditoriaPage

    init = inspect.getsource(CusteioAuditoriaPage.__init__)
    assert "Observações produção" in init
