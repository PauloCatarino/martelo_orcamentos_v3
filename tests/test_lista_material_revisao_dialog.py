from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QDialog

from app.services.lista_material_assistente_service import (
    AssistantConfig,
    AssistantSuggestion,
    MaterialRow,
    WorkbookAudit,
)
from app.ui.dialogs.lista_material_assistente_dialog import (
    ListaMaterialAssistenteDialog,
)
from app.ui.dialogs.lista_material_revisao_dialog import (
    ListaMaterialRevisaoDialog,
)


_app = QApplication.instance() or QApplication([])


def _audit() -> WorkbookAudit:
    columns = (
        "Descricao", "Material", "Comp", "Larg", "Qt", "Artigo", "Notas",
        "Orla DIR", "SourceID", "Estado_Assistente",
    )
    row = MaterialRow(
        row_number=6,
        source_id="SRC-000004",
        description="Lateral",
        material="AGL_MLM_LINHO_19MM",
        length=Decimal("2000"),
        width=Decimal("600"),
        quantity=Decimal("1"),
        article="RP_01",
        notes="",
        edges={"Orla DIR": "CNC_FRESAR"},
        values={
            "Descricao": "Lateral",
            "Material": "AGL_MLM_LINHO_19MM",
            "Comp": "2000",
            "Larg": "600",
            "Qt": "1",
            "Artigo": "RP_01",
            "Notas": "",
            "Orla DIR": "CNC_FRESAR",
            "SourceID": "SRC-000004",
            "Estado_Assistente": "POR_ANALISAR",
        },
    )
    suggestions = (
        AssistantSuggestion(
            source_id=row.source_id,
            row_number=6,
            field="Orla DIR",
            original="CNC_FRESAR",
            suggested="",
            reason="É necessário indicar a orla.",
            confidence=0.35,
            kind="cnc_fresar",
            blocking=True,
        ),
        AssistantSuggestion(
            source_id=row.source_id,
            row_number=6,
            field="Notas",
            original="",
            suggested="CNC_FRESAR; PUXADOR J H1030",
            reason="Operação CNC e puxador da obra.",
            confidence=0.92,
            kind="notas_assistente",
        ),
    )
    return WorkbookAudit(
        workbook_path=Path("lista.xlsm"),
        rows=(row,),
        suggestions=suggestions,
        blocking=(suggestions[0],),
        board_catalog_message="Modo histórico/manual.",
        columns=columns,
    )


def test_dialogo_mostra_uma_linha_por_peca_e_colunas_excel() -> None:
    audit = _audit()
    dialog = ListaMaterialRevisaoDialog(audit)

    assert dialog.table.rowCount() == 1
    assert dialog.table.columnCount() == len(audit.columns) + 3
    headers = [
        dialog.table.horizontalHeaderItem(column).text()
        for column in range(dialog.table.columnCount())
    ]
    assert headers[:11] == [
        "Decisão da peça", "Linha Excel", "Ação Assistente", "Descricao",
        "Material", "Comp", "Larg", "Qt", "Artigo", "Notas", "Orla DIR",
    ]
    assert set(headers[3:]) == set(audit.columns)
    notes_column = headers.index("Notas")
    edge_column = headers.index("Orla DIR")
    assert dialog.table.item(0, notes_column).text() == "CNC_FRESAR; PUXADOR J H1030"
    assert dialog.table.item(0, edge_column).text() == ""
    assert dialog.table.item(0, notes_column).background().color().name() == "#fff2cc"
    assert dialog.table.item(0, edge_column).background().color().name() == "#f4cccc"
    dialog.close()


def test_aceitar_seguras_deixa_apenas_bloqueio_e_edicao_resolve() -> None:
    dialog = ListaMaterialRevisaoDialog(_audit())
    headers = [
        dialog.table.horizontalHeaderItem(column).text()
        for column in range(dialog.table.columnCount())
    ]
    edge_item = dialog.table.item(0, headers.index("Orla DIR"))

    dialog._accept_safe()
    decisions = dialog.decisions()
    assert decisions[0].action == "pendente"
    assert decisions[1].action == "aceitar"
    assert "1 pendentes" in dialog.progress_label.text()

    edge_item.setText("PVC_1.0_LINHO")
    decisions = dialog.decisions()
    assert decisions[0].action == "editar"
    assert decisions[0].value == "PVC_1.0_LINHO"
    assert decisions[1].action == "aceitar"
    assert "0 pendentes" in dialog.progress_label.text()
    assert edge_item.background().color().name() == "#d9ead3"
    dialog.close()


def test_aceitar_seguras_inclui_proposta_vazia_marcada_como_valida() -> None:
    base = _audit()
    blank = AssistantSuggestion(
        source_id=base.rows[0].source_id,
        row_number=base.rows[0].row_number,
        field="Orla DIR",
        original="CNC_FRESAR",
        suggested="",
        reason="Lateral: limpar apenas CNC_FRESAR deste lado.",
        confidence=0.99,
        kind="cnc_fresar_lateral_vazio",
        blocking=False,
        allow_blank=True,
    )
    audit = WorkbookAudit(
        workbook_path=base.workbook_path,
        rows=base.rows,
        suggestions=(blank,),
        blocking=(),
        board_catalog_message=base.board_catalog_message,
        columns=base.columns,
    )
    dialog = ListaMaterialRevisaoDialog(audit)

    dialog._accept_safe()

    decisions = dialog.decisions()
    assert decisions[0].action == "aceitar"
    assert decisions[0].value == ""
    assert "0 pendentes" in dialog.progress_label.text()
    dialog.close()


def test_manter_pendentes_visiveis_resolve_bloqueio_sem_desfazer_aceites() -> None:
    dialog = ListaMaterialRevisaoDialog(_audit())

    dialog._accept_safe()
    dialog._set_all("rejeitar", visible_only=True, pending_only=True)

    decisions = dialog.decisions()
    assert decisions[0].action == "rejeitar"
    assert decisions[1].action == "aceitar"
    assert "0 pendentes" in dialog.progress_label.text()
    assert "1 mantidas sem alteração" in dialog.progress_label.text()

    dialog._validate()
    assert dialog.result() == QDialog.DialogCode.Accepted
    dialog.close()


def test_aceitacao_explicita_da_peca_valida_proposta_vazia() -> None:
    dialog = ListaMaterialRevisaoDialog(_audit())

    combo = dialog._row_actions[0]
    combo.setCurrentIndex(combo.findData("aceitar"))

    decisions = dialog.decisions()
    assert all(item.action == "aceitar" for item in decisions)
    assert decisions[0].value == ""
    assert "0 pendentes" in dialog.progress_label.text()

    dialog._validate()
    assert dialog.result() == QDialog.DialogCode.Accepted
    dialog.close()


def test_aceitar_propostas_visiveis_pode_incluir_vazios() -> None:
    dialog = ListaMaterialRevisaoDialog(_audit())

    dialog._accept_safe()
    dialog._set_all("aceitar", visible_only=True, allow_empty=True)

    decisions = dialog.decisions()
    assert decisions[0].action == "aceitar"
    assert decisions[0].value == ""
    assert decisions[1].action == "aceitar"
    assert "0 pendentes" in dialog.progress_label.text()
    dialog.close()


def test_linha_aceite_para_remocao_fica_riscada() -> None:
    base = _audit()
    removal = AssistantSuggestion(
        source_id=base.rows[0].source_id,
        row_number=base.rows[0].row_number,
        field="__DELETE_ROW__",
        original="",
        suggested="Remover; agrupada na linha 5",
        reason="Peça consolidada na linha representativa.",
        confidence=0.98,
        kind="barra_vista_vertical_remover_linha",
        delete_row=True,
        group_id="vista:SRC-000001",
    )
    audit = WorkbookAudit(
        workbook_path=base.workbook_path,
        rows=base.rows,
        suggestions=(removal,),
        blocking=(),
        board_catalog_message=base.board_catalog_message,
        columns=base.columns,
    )
    dialog = ListaMaterialRevisaoDialog(audit)
    headers = [
        dialog.table.horizontalHeaderItem(column).text()
        for column in range(dialog.table.columnCount())
    ]

    dialog._accept_safe()
    assert dialog.table.item(0, headers.index("Descricao")).font().strikeOut()
    assert dialog.table.item(0, 2).font().strikeOut()

    combo = dialog._row_actions[0]
    combo.setCurrentIndex(combo.findData("rejeitar"))
    assert not dialog.table.item(0, headers.index("Descricao")).font().strikeOut()
    dialog.close()


def test_configuracao_cnc_tem_campo_proprio_e_migra_formato_antigo() -> None:
    dialog = ListaMaterialAssistenteDialog(
        AssistantConfig(user_id=2, client="JF_VIVA", cnc_note="CNC_FRESAR")
    )
    dialog.handle_exceptions_input.setPlainText(
        "CNC_FRESAR=CNC RECORTE L\nRP_03=TIC-TAC"
    )

    config = dialog.config()

    assert config.cnc_note == "CNC RECORTE L"
    assert config.handle_exceptions == {"RP_03": "TIC-TAC"}
    dialog.close()


def test_qualquer_celula_operacional_pode_ser_editada_manualmente() -> None:
    dialog = ListaMaterialRevisaoDialog(_audit())
    headers = [
        dialog.table.horizontalHeaderItem(column).text()
        for column in range(dialog.table.columnCount())
    ]
    material_item = dialog.table.item(0, headers.index("Material"))
    source_item = dialog.table.item(0, headers.index("SourceID"))

    assert material_item.flags() & Qt.ItemFlag.ItemIsEditable
    assert not (source_item.flags() & Qt.ItemFlag.ItemIsEditable)
    material_item.setText("MDF_MR_MLM_BRANCO_B3002/MA_19MM")

    manual = [
        item for item in dialog.decisions() if item.suggestion.kind == "edicao_manual"
    ]
    assert len(manual) == 1
    assert manual[0].suggestion.field == "Material"
    assert manual[0].value == "MDF_MR_MLM_BRANCO_B3002/MA_19MM"
    assert material_item.background().color().name() == "#cfe2f3"
    dialog.close()
