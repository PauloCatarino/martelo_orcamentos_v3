"""Tests for the main application window."""

from __future__ import annotations

import inspect


def test_main_window_accepts_authenticated_user_argument() -> None:
    from app.ui.main_window import MainWindow

    signature = inspect.signature(MainWindow)

    assert "authenticated_user" in signature.parameters


def test_main_window_has_navigation_tree() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)

    assert "QTreeWidget" in source
    assert "self.nav_tree" in source
    assert "ESTILO_ARVORE_NAV" in source
    assert "_on_nav_item_clicked" in source
    assert "QPushButton(\"In" not in source


def test_main_window_has_def_pecas_navigation_inside_configuracoes() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)

    assert "ConfiguracoesPage" in source
    assert "DefPecasPage" in source
    assert "MateriasPrimasPage" in source
    assert "CaminhosSistemaPage" in source
    assert '"pecas"' in source
    assert '"materias_primas"' in source
    assert '"caminhos_sistema"' in source
    assert "pecas_button" not in source


def test_main_window_has_materias_primas_under_orcamentos() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)

    assert '"Or\\u00e7amentos", "orcamentos"' in source
    assert '"Mat\\u00e9rias-Primas", "materias_primas", parent=item_orcamentos' in source
    assert "item_orcamentos.setExpanded(True)" in source
    assert hasattr(MainWindow, "_on_nav_item_clicked")


def test_main_window_has_operacoes_maquinas_navigation_inside_configuracoes() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)

    assert "OperacoesMaquinasPage" in source
    assert '"operacoes_maquinas"' in source
    assert "on_open_operacoes_maquinas" in source
    assert "operacoes_button" not in source


def test_main_window_has_valueset_chaves_navigation_inside_configuracoes() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)

    assert "DefValuesetChavesPage" in source
    assert '"valueset_chaves"' in source
    assert "on_open_valueset_chaves" in source


def test_main_window_has_valueset_modelos_navigation_inside_configuracoes() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)

    assert "DefValuesetModelosPage" in source
    assert '"valueset_modelos"' in source
    assert "on_open_valueset_modelos" in source


def test_main_window_has_margens_padrao_navigation_inside_configuracoes() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow.__init__)

    assert "MargensPadraoPage" in source
    assert '"margens_padrao"' in source
    assert "on_open_margens_padrao" in source
    assert hasattr(MainWindow, "_open_margens_padrao")


def test_main_window_has_sidebar_toggle() -> None:
    from app.ui.main_window import MainWindow

    assert hasattr(MainWindow, "toggle_sidebar")

    init = inspect.getsource(MainWindow.__init__)
    assert "toggle_sidebar_button" in init
    assert "self.sidebar" in init

    toggle = inspect.getsource(MainWindow.toggle_sidebar)
    assert "setVisible" in toggle
    assert "_sidebar_visivel" in toggle  # tracked flag, not isVisible()
