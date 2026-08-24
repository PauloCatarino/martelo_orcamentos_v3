from __future__ import annotations

import inspect


def test_dialogo_pdf_carrega_preset_predefinido_e_isola_utilizador() -> None:
    from app.ui.dialogs.lista_material_pdf_dialog import ListaMaterialPdfDialog

    init_source = inspect.getsource(ListaMaterialPdfDialog.__init__)
    reload_source = inspect.getsource(ListaMaterialPdfDialog._reload_presets)
    save_source = inspect.getsource(ListaMaterialPdfDialog._save_preset)

    assert "self._reload_presets(apply_default=True)" in init_source
    assert "self.default_preset_check" in init_source
    assert "user_id=self.user_id" in reload_source
    assert "preset.predefinido" in reload_source
    assert "make_default=self.default_preset_check.isChecked()" in save_source
