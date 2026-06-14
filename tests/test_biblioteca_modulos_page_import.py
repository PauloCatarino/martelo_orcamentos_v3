"""Import checks for the module-library page and its dialogs (phase 8U.3)."""

from __future__ import annotations

import dataclasses
import inspect


def test_biblioteca_modulos_page_imports() -> None:
    from app.ui.pages.biblioteca_modulos_page import BibliotecaModulosPage

    assert BibliotecaModulosPage.TABLE_HEADERS == [
        "Imagem",
        "Código",
        "Nome",
        "Categoria",
        "Âmbito",
        "Nº linhas",
        "Criado em",
    ]
    for method in (
        "carregar",
        "editar_modulo",
        "eliminar_modulo",
        "ver_linhas",
        "_modulo_selecionado",
    ):
        assert hasattr(BibliotecaModulosPage, method)

    # Search ('%') + category filter + own/global tabs.
    init = inspect.getsource(BibliotecaModulosPage.__init__)
    assert "pesquisa_input" in init
    assert "categoria_filtro" in init
    assert "Utilizador" in init and "Global" in init

    carregar = inspect.getsource(BibliotecaModulosPage.carregar)
    assert "listar_modulos_para_dialogo" in carregar

    # Edit reuses editar_cabecalho; delete reuses eliminar; view uses obter.
    editar = inspect.getsource(BibliotecaModulosPage.editar_modulo)
    assert "editar_cabecalho" in editar
    assert "EditarModuloDialog" in editar
    eliminar = inspect.getsource(BibliotecaModulosPage.eliminar_modulo)
    assert "eliminar" in eliminar
    assert "QMessageBox" in eliminar
    assert "definitiva" in eliminar  # clear, irreversible confirmation
    ver = inspect.getsource(BibliotecaModulosPage.ver_linhas)
    assert "obter_com_linhas" in ver
    assert "ModuloLinhasDialog" in ver


def test_editar_modulo_dialog_imports() -> None:
    from app.ui.dialogs.editar_modulo_dialog import (
        EditarModuloDialog,
        EditarModuloDialogData,
    )

    fields = {f.name for f in dataclasses.fields(EditarModuloDialogData)}
    assert fields == {"nome", "descricao", "ambito", "categoria", "imagem_path"}

    init = inspect.getsource(EditarModuloDialog.__init__)
    assert "on_save" in init
    assert "setReadOnly" in init  # the code is fixed
    procurar = inspect.getsource(EditarModuloDialog._procurar_imagem)
    assert "QFileDialog" in procurar


def test_modulo_linhas_dialog_imports() -> None:
    from app.ui.dialogs.modulo_linhas_dialog import ModuloLinhasDialog

    assert ModuloLinhasDialog._COLUNAS == (
        "Tipo",
        "Código/Def. peça",
        "Descrição",
        "QT",
        "Comp",
        "Larg",
        "Esp",
    )


def test_configuracoes_page_has_biblioteca_modulos_button() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    parameters = inspect.signature(ConfiguracoesPage).parameters
    assert "on_open_biblioteca_modulos" in parameters

    init_source = inspect.getsource(ConfiguracoesPage.__init__)
    assert "Biblioteca de Módulos" in init_source
    assert "biblioteca_modulos_button" in init_source


def test_main_window_wires_biblioteca_modulos() -> None:
    from app.ui.main_window import MainWindow

    source = inspect.getsource(MainWindow)
    assert "BibliotecaModulosPage" in source
    assert "biblioteca_modulos" in source
    assert "_open_biblioteca_modulos" in source
