"""Import checks for the import-module dialog and page wiring (phase 8U.2)."""

from __future__ import annotations

import inspect

from app.domain.modulo_categorias import normalize_modulo_categoria
from app.domain.modulo_pesquisa import modulo_corresponde, termo_tokens


def test_importar_modulo_dialog_imports() -> None:
    from app.ui.dialogs.importar_modulo_dialog import ImportarModuloDialog

    init = inspect.getsource(ImportarModuloDialog.__init__)
    assert "modulos_utilizador" in init
    assert "modulos_globais" in init
    assert "obter_linhas" in init
    assert "Importar Módulo" in init

    # List panel: search ('%') + category filter + own/global tabs.
    lista = inspect.getsource(ImportarModuloDialog._criar_painel_lista)
    assert "pesquisa_input" in lista
    assert "categoria_filtro" in lista

    # Preview panel: bigger image + name + description + the module lines.
    preview = inspect.getsource(ImportarModuloDialog._criar_painel_preview)
    assert "preview_imagem" in preview
    assert "preview_linhas" in preview

    # A missing/unreadable image falls back to a placeholder.
    pixmap = inspect.getsource(ImportarModuloDialog._pixmap)
    assert "isNull" in pixmap
    ajustar = inspect.getsource(ImportarModuloDialog._ajustar_imagem_preview)
    assert "Sem imagem" in ajustar

    # Resizable layout: splitters (panels + image/lines) and drag-resizable cols.
    init = inspect.getsource(ImportarModuloDialog.__init__)
    assert "QSplitter" in init
    assert "setSizeGripEnabled" in init
    colunas = inspect.getsource(ImportarModuloDialog._configurar_colunas)
    assert "Interactive" in colunas
    assert "setStretchLastSection" in colunas
    preview_panel = inspect.getsource(ImportarModuloDialog._criar_painel_preview)
    assert "QSplitter" in preview_panel


def test_custeio_page_importar_modulo_wiring() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert hasattr(OrcamentoItemCusteioPage, "importar_modulo")

    init = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    # The button is now active and wired to the handler.
    assert "import_module_button" in init
    assert "self.importar_modulo" in init

    handler = inspect.getsource(OrcamentoItemCusteioPage.importar_modulo)
    assert "ImportarModuloDialog" in handler
    assert "listar_modulos_para_dialogo" in handler
    assert "inserir_modulo_no_item" in handler
    assert "_recalcular_item_completo" in handler


def test_dialog_filter_logic_percent_and_category() -> None:
    """The dialog filters by category then '%'-separated AND tokens (shared)."""

    class _Modulo:
        def __init__(self, codigo, nome, categoria):
            self.codigo = codigo
            self.nome = nome
            self.descricao = None
            self.categoria = categoria

    modulos = [
        _Modulo("ROUP_CANTO", "Roupeiro de canto 2 portas", "ROUPEIROS"),
        _Modulo("ROUP_RETO", "Roupeiro reto 3 portas", "ROUPEIROS"),
        _Modulo("COZ_BASE", "Cozinha base", "COZINHAS"),
    ]

    def filtrar(itens, categoria, termo):
        tokens = termo_tokens(termo)
        return [
            m
            for m in itens
            if (not categoria or normalize_modulo_categoria(m.categoria) == categoria)
            and modulo_corresponde(m, tokens)
        ]

    # '%' tokens: ALL must match.
    canto = filtrar(modulos, None, "canto%2 portas")
    assert [m.codigo for m in canto] == ["ROUP_CANTO"]

    # Category filter narrows to one zone.
    roupeiros = filtrar(modulos, "ROUPEIROS", "")
    assert {m.codigo for m in roupeiros} == {"ROUP_CANTO", "ROUP_RETO"}

    # Category + term combined.
    coz = filtrar(modulos, "COZINHAS", "base")
    assert [m.codigo for m in coz] == ["COZ_BASE"]
