"""Import checks for the per-user piece library preferences dialog."""

from __future__ import annotations

import inspect


def test_dialog_imports() -> None:
    from app.ui.dialogs.preferencias_biblioteca_pecas_dialog import (
        PreferenciasBibliotecaPecasDialog,
    )

    assert PreferenciasBibliotecaPecasDialog is not None


def test_dialog_uses_pref_service_and_search() -> None:
    from app.ui.dialogs.preferencias_biblioteca_pecas_dialog import (
        PreferenciasBibliotecaPecasDialog,
    )

    source = inspect.getsource(PreferenciasBibliotecaPecasDialog._carregar)
    assert "DefPecaUserPrefService" in source
    assert "listar_ativas_para_biblioteca" in source

    init = inspect.getsource(PreferenciasBibliotecaPecasDialog.__init__)
    assert "CampoPesquisa" in init
    assert "Repor (mostrar todas)" in init


def test_dialog_keeps_favorito_disponivel() -> None:
    from app.ui.dialogs.preferencias_biblioteca_pecas_dialog import (
        PreferenciasBibliotecaPecasDialog,
    )

    source = inspect.getsource(PreferenciasBibliotecaPecasDialog._on_item_changed)
    assert "setCheckState" in source


def test_dialog_exposes_alterado() -> None:
    from app.ui.dialogs.preferencias_biblioteca_pecas_dialog import (
        PreferenciasBibliotecaPecasDialog,
    )

    assert isinstance(
        inspect.getattr_static(PreferenciasBibliotecaPecasDialog, "alterado"),
        property,
    )


def test_custeio_page_filtra_por_preferencias() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    carregar = inspect.getsource(OrcamentoItemCusteioPage._carregar_biblioteca)
    assert "obter_preferencias" in carregar

    preencher = inspect.getsource(OrcamentoItemCusteioPage._preencher_biblioteca)
    assert "peca_visivel" in preencher


def test_configuracoes_page_tem_botao() -> None:
    from app.ui.pages.configuracoes_page import ConfiguracoesPage

    assert "A Minha Biblioteca de Peças" in ConfiguracoesPage.TECHNICAL_AREAS
    assert hasattr(ConfiguracoesPage, "_open_minha_biblioteca_pecas")
