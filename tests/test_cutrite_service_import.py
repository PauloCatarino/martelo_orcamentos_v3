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


def test_lista_material_ilegivel_da_erro_claro_sem_abrir_o_excel(tmp_path, monkeypatch) -> None:
    """Sem o plano B do Excel escondido: as MsgBox das macros deixavam o envio parado."""
    import pytest

    import app.services.cutrite_service as service

    def _excel_proibido(*_args, **_kwargs):
        raise AssertionError("o envio para o CUT-RITE nao pode abrir o Excel")

    monkeypatch.setattr("win32com.client.DispatchEx", _excel_proibido, raising=False)
    estragado = tmp_path / "Lista_Material_9999_01_26_TESTE.xlsm"
    estragado.write_bytes(b"isto nao e um Excel")

    with pytest.raises(ValueError) as erro:
        service._load_cutrite_source_table(estragado)

    mensagem = str(erro.value)
    assert "Nao consegui ler a Lista Material" in mensagem
    assert "Grave e feche o Excel" in mensagem
    assert str(estragado) in mensagem
    assert not hasattr(service, "_load_cutrite_source_table_from_excel_macro")
    assert "_run_excel_macro" not in inspect.getsource(service)


def test_lista_material_sem_listagem_cut_rite_diz_qual_separador(tmp_path) -> None:
    import pytest
    from openpyxl import Workbook

    import app.services.cutrite_service as service

    livro = Workbook()
    livro.active.title = "OUTRA"
    caminho = tmp_path / "Lista_Material_9999_01_26_TESTE.xlsx"
    livro.save(caminho)

    with pytest.raises(ValueError, match="nao tem o separador LISTAGEM_CUT_RITE"):
        service._load_cutrite_source_table(caminho)
