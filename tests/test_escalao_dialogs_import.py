"""Import checks for the CNC area-tier dialogs and repository (phase 8S.0)."""

from __future__ import annotations

import dataclasses
import inspect


def test_escalao_dialog_imports() -> None:
    from app.ui.dialogs.escalao_area_dialog import (
        EscalaoAreaDialog,
        EscalaoAreaDialogData,
    )

    campos = {f.name for f in dataclasses.fields(EscalaoAreaDialogData)}
    assert {
        "nivel",
        "area_max_m2",
        "preco_peca_std",
        "preco_peca_serie",
        "ativo",
    } <= campos
    assert hasattr(EscalaoAreaDialog, "get_data")


def test_escalao_dialog_sufixos_e_2_casas() -> None:
    from app.ui.dialogs.escalao_area_dialog import EscalaoAreaDialog

    criar = inspect.getsource(EscalaoAreaDialog._criar_spin)
    assert "QDoubleSpinBox" in criar
    assert "setSuffix" in criar
    assert "setDecimals(2)" in criar

    init = inspect.getsource(EscalaoAreaDialog.__init__)
    assert " m2" in init
    assert "€/peça" in init

    # Decimal is kept on save.
    spin_to_decimal = inspect.getsource(EscalaoAreaDialog._spin_to_decimal)
    assert "Decimal" in spin_to_decimal


def test_escaloes_table_formata_area() -> None:
    from decimal import Decimal

    from app.ui.dialogs.escaloes_area_dialog import EscaloesAreaDialog

    assert EscaloesAreaDialog._format_area(None) == "Sem limite"
    assert EscaloesAreaDialog._format_area(Decimal("0.3")) == "0,30 m2"
    assert EscaloesAreaDialog._format_area(Decimal("2")) == "2,00 m2"
    assert EscaloesAreaDialog._format_area(Decimal("0.5000")) == "0,50 m2"


def test_escaloes_dialog_imports_and_actions() -> None:
    from app.ui.dialogs.escaloes_area_dialog import EscaloesAreaDialog

    for method in (
        "carregar",
        "abrir_novo_escalao",
        "abrir_editar_escalao",
        "alternar_escalao_ativo",
    ):
        assert hasattr(EscaloesAreaDialog, method)

    # Uses the area-tier service and never deletes (only toggles).
    source = inspect.getsource(EscaloesAreaDialog)
    assert "DefMaquinaEscalaoAreaService" in source
    assert "desativar_escalao" in source


def test_escalao_repository_resumo_fields() -> None:
    from app.repositories.def_maquina_escalao_area_repository import (
        DefMaquinaEscalaoAreaRepository,
        DefMaquinaEscalaoAreaResumo,
    )

    campos = {f.name for f in dataclasses.fields(DefMaquinaEscalaoAreaResumo)}
    assert {
        "def_maquina_id",
        "nivel",
        "area_max_m2",
        "preco_peca_std",
        "preco_peca_serie",
        "ativo",
    } <= campos

    for method in (
        "list_by_maquina",
        "list_active_by_maquina",
        "create_escalao",
        "update_escalao",
        "deactivate_escalao",
        "activate_escalao",
    ):
        assert hasattr(DefMaquinaEscalaoAreaRepository, method)
