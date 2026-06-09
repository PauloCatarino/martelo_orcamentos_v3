"""Import checks for the finishing-edit dialog (phase 8O.1)."""

from __future__ import annotations

import inspect


def test_acabamento_dialog_imports() -> None:
    from app.ui.dialogs.custeio_linha_acabamento_dialog import (
        CusteioLinhaAcabamentoDialog,
    )

    assert CusteioLinhaAcabamentoDialog is not None


def test_acabamento_dialog_tem_duas_faces_e_picker() -> None:
    from app.ui.dialogs.custeio_linha_acabamento_dialog import (
        CusteioLinhaAcabamentoDialog,
    )

    init = inspect.getsource(CusteioLinhaAcabamentoDialog.__init__)
    assert "Face superior" in init
    assert "Face inferior" in init

    assert hasattr(CusteioLinhaAcabamentoDialog, "_selecionar")
    selecionar = inspect.getsource(CusteioLinhaAcabamentoDialog._selecionar)
    assert "MateriaPrimaPickerDialog" in selecionar
    assert "preco" in selecionar


def test_acabamento_dialog_get_data_campos() -> None:
    from app.ui.dialogs.custeio_linha_acabamento_dialog import (
        CusteioLinhaAcabamentoDialog,
    )

    # get_data builds the field names with f-strings over ("sup", "inf").
    get_data = inspect.getsource(CusteioLinhaAcabamentoDialog.get_data)
    for fragmento in (
        "acabamento_face_",
        "_ref_le",
        "_descricao",
        "_unidade",
        "_preco_liquido",
        "_desperdicio_percentagem",
    ):
        assert fragmento in get_data


def test_acabamento_dialog_formata_euro_e_percentagem() -> None:
    from app.ui.dialogs.custeio_linha_acabamento_dialog import (
        CusteioLinhaAcabamentoDialog,
    )

    fmt_preco = inspect.getsource(CusteioLinhaAcabamentoDialog._format_preco)
    assert "format_currency" in fmt_preco

    fmt_desp = inspect.getsource(CusteioLinhaAcabamentoDialog._format_desp)
    assert "formatar_percentagem" in fmt_desp
    assert "normalize_percentagem_humana" in fmt_desp

    # On save the price is parsed via parse_decimal_humano (strips "€"/",") and the
    # waste is normalized to a human percentage (0.01 -> 1).
    parse_desp = inspect.getsource(CusteioLinhaAcabamentoDialog._parse_desp)
    assert "normalize_percentagem_humana" in parse_desp


def test_acabamento_dialog_filtra_familia_acabamento() -> None:
    from app.ui.dialogs.custeio_linha_acabamento_dialog import (
        CusteioLinhaAcabamentoDialog,
    )

    selecionar = inspect.getsource(CusteioLinhaAcabamentoDialog._selecionar)
    assert "initial_familia=FAMILIA_ACABAMENTO" in selecionar
