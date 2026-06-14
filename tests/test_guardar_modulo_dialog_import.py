"""Import checks for the save-as-module dialog and page wiring (phase 8U.1)."""

from __future__ import annotations

import dataclasses
import inspect


def test_guardar_modulo_dialog_imports() -> None:
    from app.ui.dialogs.guardar_modulo_dialog import (
        GuardarModuloDialog,
        GuardarModuloDialogData,
    )

    fields = {f.name for f in dataclasses.fields(GuardarModuloDialogData)}
    assert fields == {
        "codigo",
        "nome",
        "descricao",
        "ambito",
        "categoria",
        "imagem_path",
        "modulo_id",
    }

    init = inspect.getsource(GuardarModuloDialog.__init__)
    assert "on_save" in init
    assert "modulos_utilizador" in init
    assert "modulos_globais" in init
    # Image: path field + browse button (QFileDialog).
    procurar = inspect.getsource(GuardarModuloDialog._procurar_imagem)
    assert "QFileDialog" in procurar

    # Replace mode + "Novo" button + the saved-modules list panel.
    novo = inspect.getsource(GuardarModuloDialog._aplicar_modo_novo)
    assert "Guardar" in novo
    substituir = inspect.getsource(GuardarModuloDialog._aplicar_modo_substituir)
    assert "Substituir" in substituir
    lista = inspect.getsource(GuardarModuloDialog._criar_painel_lista)
    assert "categoria_filtro" in lista
    assert "pesquisa_input" in lista
    confirmar = inspect.getsource(GuardarModuloDialog._confirmar_substituicao)
    assert "QMessageBox" in confirmar


def test_legacy_novo_modulo_dialog_preserved() -> None:
    # The unrelated legacy dialog must keep working (per-item modules page).
    from app.ui.dialogs.novo_modulo_dialog import NovoModuloDialog

    assert NovoModuloDialog is not None


def test_custeio_page_guardar_como_modulo() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    for method in (
        "guardar_como_modulo",
        "_ids_linhas_selecionadas",
        "_atualizar_botao_modulo",
    ):
        assert hasattr(OrcamentoItemCusteioPage, method)

    init = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    assert "guardar_modulo_button" in init
    assert "Guardar como Módulo" in init
    # Button enabled by the selection.
    assert "itemSelectionChanged" in init

    handler = inspect.getsource(OrcamentoItemCusteioPage.guardar_como_modulo)
    assert "guardar_de_linhas_custeio" in handler
    assert "substituir_de_linhas_custeio" in handler
    assert "listar_modulos_para_dialogo" in handler
    assert "GuardarModuloDialog" in handler
    assert "app_session.current_user" in handler
