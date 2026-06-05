"""Import checks for the Orcamento modules tab."""

from __future__ import annotations


def test_orcamento_modulos_tab_imports() -> None:
    from app.ui.pages.orcamento_modulos_tab import OrcamentoModulosTab

    assert OrcamentoModulosTab is not None


def test_orcamento_modulos_tab_exposes_set_item() -> None:
    from app.ui.pages.orcamento_modulos_tab import OrcamentoModulosTab

    assert hasattr(OrcamentoModulosTab, "set_item")
