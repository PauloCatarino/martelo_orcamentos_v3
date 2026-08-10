"""UI wiring checks for explicit global ValueSet replacement."""

from __future__ import annotations

import inspect


def test_dialogo_mostra_lista_impacto_e_supervisor() -> None:
    from app.ui.dialogs.substituir_valueset_modelo_dialog import (
        SubstituirValuesetModeloDialog,
    )

    source = inspect.getsource(SubstituirValuesetModeloDialog)
    assert "Código" in SubstituirValuesetModeloDialog.HEADERS
    assert "Linhas" in SubstituirValuesetModeloDialog.HEADERS
    assert "Operações" in SubstituirValuesetModeloDialog.HEADERS
    assert "supervisor_label" in source
    assert "Substituir selecionado" in source
    assert "setToolTip" in source


def test_publicacao_exige_selecao_confirmacao_e_permissao() -> None:
    from app.ui.helpers.valueset_modelo_publicacao import (
        publicar_modelo_valueset_para_todos,
    )

    source = inspect.getsource(publicar_modelo_valueset_para_todos)
    assert "PERMISSAO_PUBLICAR_MODELO_VALUESET_GLOBAL" in source
    assert "selected_destino" in source
    assert "Confirmar substituição integral" in source
    assert "substituir_modelo_global" in source


def test_gravar_como_global_usa_publicacao_nas_duas_paginas() -> None:
    from app.ui.pages.def_valueset_modelo_detail_page import (
        DefValuesetModeloDetailPage,
    )
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage

    lista = inspect.getsource(DefValuesetModelosPage.abrir_editar_modelo)
    detalhe = inspect.getsource(DefValuesetModeloDetailPage.gravar_modelo_como)
    for source in (lista, detalhe):
        assert '== "GLOBAL"' in source
        assert "publicar_modelo_valueset_para_todos" in source
        assert "PermissionError" in source
