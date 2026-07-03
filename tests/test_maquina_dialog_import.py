"""Import checks for the machine dialog."""

from __future__ import annotations

import dataclasses
import inspect


def test_maquina_dialog_imports() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog, MaquinaDialogData

    assert MaquinaDialog is not None
    assert MaquinaDialogData is not None


def test_maquina_dialog_accepts_maquina_and_callback() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    signature = inspect.signature(MaquinaDialog)

    assert "maquina" in signature.parameters
    assert "on_save" in signature.parameters
    assert hasattr(MaquinaDialog, "set_error")


def test_maquina_dialog_data_fields() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialogData

    field_names = {field.name for field in dataclasses.fields(MaquinaDialogData)}

    assert {
        "codigo",
        "nome",
        "descricao",
        "tipo",
        "custo_hora",
        "observacoes",
        "ativo",
    } <= field_names


def test_maquina_dialog_tipo_options() -> None:
    from app.ui.dialogs.maquina_dialog import TIPO_OPCOES

    assert TIPO_OPCOES == ("CORTE", "ORLAGEM", "CNC", "MONTAGEM", "MANUAL", "OUTRO")


def test_maquina_dialog_uses_combobox_for_tipo() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    source_names = MaquinaDialog.__init__.__code__.co_names

    assert "QComboBox" in source_names


def test_maquina_dialog_spin_to_decimal() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    source = inspect.getsource(MaquinaDialog._spin_to_decimal)

    assert "Decimal" in source


def test_maquina_dialog_tem_tarifas_std_serie() -> None:
    import dataclasses

    from app.ui.dialogs.maquina_dialog import MaquinaDialog, MaquinaDialogData

    campos = {f.name for f in dataclasses.fields(MaquinaDialogData)}
    assert {
        "custo_hora",
        "custo_hora_serie",
        "preco_ml_std",
        "preco_ml_serie",
        "preco_lado_curto_std",
        "preco_lado_curto_serie",
        "preco_lado_longo_std",
        "preco_lado_longo_serie",
        "limite_lado_mm",
        "custo_setup_peca_std",
        "custo_setup_peca_serie",
    } <= campos

    # Units are shown as spin-box suffixes and the tariff section adapts to type.
    init = inspect.getsource(MaquinaDialog.__init__)
    assert "QDoubleSpinBox" in MaquinaDialog._criar_spin.__code__.co_names
    for sufixo in ("€/H", "€/ML", "€/lado", "mm", "€/peça"):
        assert sufixo in init


def test_maquina_dialog_adapta_campos_ao_tipo() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    assert hasattr(MaquinaDialog, "_update_tarifas_visiveis")
    source = inspect.getsource(MaquinaDialog._update_tarifas_visiveis)
    for tipo in ("CORTE", "ORLAGEM", "CNC", "MANUAL", "MONTAGEM"):
        assert tipo in source
    assert "hora_section" in source
    assert "ml_section" in source
    assert "orlagem_section" in source
    assert "setup_section" in source
    assert "cnc_section" in source

    # CNC area-tier editor is reachable from the dialog.
    assert hasattr(MaquinaDialog, "_abrir_escaloes")
    abrir = inspect.getsource(MaquinaDialog._abrir_escaloes)
    assert "EscaloesAreaDialog" in abrir


def test_maquina_dialog_blocks_codigo_on_edit() -> None:
    from app.ui.dialogs.maquina_dialog import MaquinaDialog

    source = inspect.getsource(MaquinaDialog._load_maquina)

    assert "setReadOnly" in source
