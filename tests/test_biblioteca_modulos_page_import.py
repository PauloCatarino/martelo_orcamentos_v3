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
    assert "colapsar_button" not in init
    assert "alternar_expansao" in init
    assert init.index("buttons_layout.addWidget(self.atualizar_button)") < init.index(
        'buttons_layout.addWidget(QLabel("Categoria"))'
    )
    assert init.index("buttons_layout.addWidget(self.gerir_categorias_button)") < init.index(
        "buttons_layout.addStretch()"
    )

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
    assert fields == {
        "nome",
        "descricao",
        "ambito",
        "categoria",
        "subcategoria",
        "imagem_path",
    }

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
        "Prioridade",
        "QT",
        "Comp",
        "Larg",
        "Esp",
    )


def test_biblioteca_alterna_expandir_e_colapsar_num_mesmo_botao(
    monkeypatch,
) -> None:
    from PySide6.QtWidgets import QApplication, QTreeWidgetItem

    from app.ui.pages.biblioteca_modulos_page import BibliotecaModulosPage

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(BibliotecaModulosPage, "carregar", lambda self: None)
    pagina = BibliotecaModulosPage()
    categoria = QTreeWidgetItem(["ROUPEIROS"])
    subcategoria = QTreeWidgetItem(["ROUPEIROS_ABRIR"])
    modulo = QTreeWidgetItem(["MODULO_TESTE"])
    subcategoria.addChild(modulo)
    categoria.addChild(subcategoria)
    pagina.arvore_utilizador.addTopLevelItem(categoria)

    pagina._atualizar_botao_expansao()
    assert pagina.expandir_button.text() == pagina._TEXTO_EXPANDIR_TUDO

    pagina.alternar_expansao()
    assert categoria.isExpanded()
    assert subcategoria.isExpanded()
    assert pagina.expandir_button.text() == pagina._TEXTO_COLAPSAR_TUDO

    pagina.alternar_expansao()
    assert not categoria.isExpanded()
    assert not subcategoria.isExpanded()
    assert pagina.expandir_button.text() == pagina._TEXTO_EXPANDIR_TUDO
    pagina.deleteLater()
    app.processEvents()


def test_dialogos_da_biblioteca_abrem_maiores_e_redimensionaveis(
    monkeypatch,
) -> None:
    from PySide6.QtWidgets import QApplication

    from app.ui.dialogs.gerir_categorias_modulos_dialog import (
        GerirCategoriasModulosDialog,
    )
    from app.ui.dialogs.modulo_linhas_dialog import ModuloLinhasDialog

    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(GerirCategoriasModulosDialog, "_carregar", lambda self: None)
    linhas = ModuloLinhasDialog()
    categorias = GerirCategoriasModulosDialog()

    assert linhas.minimumWidth() == 820
    assert linhas.minimumHeight() == 650
    assert linhas.width() >= 950
    assert linhas.height() >= 840
    assert linhas.isSizeGripEnabled()
    assert categorias.minimumWidth() == 760
    assert categorias.minimumHeight() == 560
    assert categorias.width() >= 900
    assert categorias.height() >= 700
    assert categorias.isSizeGripEnabled()

    linhas.deleteLater()
    categorias.deleteLater()
    app.processEvents()


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
