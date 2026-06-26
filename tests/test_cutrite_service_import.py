"""Import checks for CUT-RITE automation service."""

from __future__ import annotations

import inspect


def test_cutrite_service_exports_resumo_pdf_helpers() -> None:
    import app.services.cutrite_service as service

    source = inspect.getsource(service)

    assert service.MS_PRINT_TO_PDF_NAME == "Microsoft Print to PDF"
    assert service.CUTRITE_PRINT_VIEWS_MENU_FRAGMENT == "imprimir as visualizacoes"
    assert service.CUTRITE_PRINT_PREVIEW_TITLE_FRAGMENT == "vista de impressao"
    assert service.CUTRITE_PDF_MENU_DELAY_SECONDS == 1.2
    assert service.CUTRITE_PDF_DIALOG_SETTLE_SECONDS == 1.0
    assert hasattr(service, "CutRiteResumoPdfContext")
    assert hasattr(service, "prepare_cutrite_resumo_pdf")
    assert hasattr(service, "execute_cutrite_resumo_pdf")
    assert "_open_cutrite_print_views_menu" in source
    assert 'keyboard.send_keys("i", pause=0.08)' in source
    assert "timeout_seconds=35" in source
    assert "timeout_seconds=90" in source
    assert "_find_cutrite_print_preview_window" in source
    assert "_find_cutrite_dialog_with_button" in source
    assert "_select_cutrite_pdf_printer" in source
    assert "_set_cutrite_save_filename" in source
    assert "_wait_for_cutrite_pdf_file" in source
