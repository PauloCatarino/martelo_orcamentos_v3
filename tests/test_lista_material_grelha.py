"""Grelha tipo Excel da LISTAGEM_CUT_RITE (pedido do Paulo, obra lowcost 1568).

Ensaio no Excel real (cópia da 1568, 21-09-2026): 278 células, 69 linhas
eliminadas e 1 colada em 18,8 s, zero diferenças; a linha colada calculou
sozinha Ref_Cliente, Processo, ID e Esp.Mat (colunas com fórmula).
"""
from __future__ import annotations

from decimal import Decimal

import pytest
from openpyxl import Workbook
from PySide6.QtWidgets import QApplication

from app.services.lista_material_assistente_service import AssistantSuggestion, MaterialRow
from app.services.lista_material_grelha_service import GrelhaListagem, colunas_com_formula
from app.ui.dialogs.grelha_listagem_dialog import GrelhaListagemDialog

COLS = ("Descricao", "Material", "Comp", "Qt", "Notas", "Orla ESQ", "Ref_Cliente", "ID", "SourceID")


def _row(n, descricao, notas="", orla=""):
    values = {"Descricao": descricao, "Material": "AGL", "Comp": "2400", "Qt": "1", "Notas": notas,
              "Orla ESQ": orla, "Ref_Cliente": "2604025", "ID": str(n - 2), "SourceID": ""}
    return MaterialRow(row_number=n, source_id=str(n), description=descricao, material="AGL",
                       length=Decimal("2400"), width=None, quantity=Decimal("1"), article="",
                       notes=notas, edges={"Orla ESQ": orla}, values=values)


def _sug(n, field, value, *, delete=False, blocking=False):
    return AssistantSuggestion(source_id=str(n), row_number=n, field=field, original="",
                               suggested=value, reason="teste", confidence=0.9, kind="k",
                               delete_row=delete, blocking=blocking)


@pytest.fixture
def grelha():
    rows = [_row(3, "Costa"), _row(4, "Teto"), _row(5, "Rodape Frente"), _row(6, "Maleiro", orla="CNC_FRESAR")]
    sugs = [_sug(3, "Notas", "PISO 1º - F"), _sug(5, "__DELETE_ROW__", "", delete=True),
            _sug(6, "Orla ESQ", "", blocking=True)]
    return GrelhaListagem(COLS, rows, sugs, formula_columns={"Ref_Cliente", "ID"})


def test_propostas_ja_aparecem_aplicadas(grelha):
    assert grelha.rows[0].values["Notas"] == "PISO 1º - F"
    assert grelha.cell_state(0, "Notas") == "proposta"
    assert grelha.rows[2].removed and grelha.row_state(2) == "A remover"
    assert grelha.cell_state(3, "Orla ESQ") == "confirmar"   # bloqueante: fica o valor atual
    assert grelha.edits() == [(3, "Notas", "PISO 1º - F")]
    assert grelha.deletions() == [5]


def test_formulas_e_tecnicas_nao_se_editam(grelha):
    assert not grelha.set_value(1, "Ref_Cliente", "X")
    assert not grelha.set_value(1, "ID", "9")
    assert not grelha.set_value(1, "SourceID", "9")
    assert grelha.set_value(1, "Notas", "MONTADO")
    assert grelha.cell_state(1, "Notas") == "editada"


def test_copiar_colar_antes_e_depois(grelha):
    grelha.copy_rows([1])
    grelha.paste_rows(1, after=True)
    grelha.paste_rows(0, after=False)
    assert [r.values["Descricao"] for r in grelha.rows] == ["Teto", "Costa", "Teto", "Teto", "Rodape Frente", "Maleiro"]
    nova = grelha.rows[0]
    assert nova.is_new and nova.values["Ref_Cliente"] == "" and nova.values["ID"] == ""
    ordem = grelha.final_order()
    assert ordem[0] == {"Descricao": "Teto", "Material": "AGL", "Comp": "2400", "Qt": "1",
                        "Notas": "", "Orla ESQ": ""}
    assert ordem[1] == 3 and 5 not in ordem   # a linha 5 sai
    assert grelha.summary() == (1, 1, 2)


def test_eliminar_limpar_e_repor(grelha):
    grelha.copy_rows([0])
    grelha.paste_rows(0, after=True)
    grelha.delete_rows([1])                     # nova: desaparece
    assert len(grelha.rows) == 4
    grelha.delete_rows([1])                     # do Excel: fica riscada
    assert grelha.rows[1].removed
    assert grelha.clear_cells([(0, "Notas"), (0, "Ref_Cliente")]) == 1
    grelha.restore_rows([0, 1, 2])
    assert grelha.rows[0].values["Notas"] == "" and not grelha.rows[1].removed
    assert grelha.edits() == [] and grelha.deletions() == []


def test_decisoes_para_a_aprendizagem(grelha):
    grelha.set_value(3, "Orla ESQ", "PVC_0.4_LINHO")
    acoes = sorted((d.suggestion.row_number, d.action) for d in grelha.decisions())
    assert acoes == [(3, "aceitar"), (5, "aceitar"), (6, "editar")]
    grelha.restore_rows([0])
    assert (3, "rejeitar") in [(d.suggestion.row_number, d.action) for d in grelha.decisions()]


def test_colunas_com_formula(tmp_path):
    w = Workbook()
    w.active.title = "LISTAGEM_CUT_RITE"
    w.active.append(["x"])
    w.active.append(["Descricao", "Ref_Cliente", "ID"])
    w.active.append(["Costa", "=RefCliente_CutRite()", "=ROW()-2"])
    caminho = tmp_path / "l.xlsx"
    w.save(caminho)
    assert colunas_com_formula(caminho) == {"Ref_Cliente", "ID"}


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_dialogo_filtra_como_o_excel(app, grelha):
    dialogo = GrelhaListagemDialog(grelha)
    try:
        coluna = dialogo.model.columns.index("Descricao") + 2
        dialogo.proxy.set_filter(coluna, {"Teto", "Costa"})
        assert dialogo.proxy.rowCount() == 2
        dialogo._mark_header()
        assert dialogo.model.headerData(coluna, __import__("PySide6.QtCore").QtCore.Qt.Orientation.Horizontal).endswith("▼")
        dialogo._clear_filters()
        dialogo.only_changes.setChecked(True)
        assert dialogo.proxy.rowCount() == 3     # Costa (proposta), Rodapé (remover), Maleiro (confirmar)
        assert "1 células, 1 linhas eliminadas, 0 linhas novas" in dialogo.summary.text()
    finally:
        dialogo.close()


def test_ctrl_z_desfaz_colar_eliminar_limpar_e_editar(grelha):
    """Pedido do Paulo (21-09-2026): colou uma linha e não conseguiu voltar atrás."""
    antes = [(r.original_row, dict(r.values), r.removed) for r in grelha.rows]
    assert not grelha.can_undo()
    grelha.copy_rows([1])
    grelha.paste_rows(1, after=True)
    assert len(grelha.rows) == 5
    assert grelha.undo() and len(grelha.rows) == 4
    assert grelha.redo() and len(grelha.rows) == 5
    assert grelha.undo()
    grelha.delete_rows([0])
    grelha.clear_cells([(1, "Notas"), (1, "Descricao"), (2, "Descricao")])   # uma operação
    grelha.set_value(3, "Notas", "RECORTE L")
    grelha.set_value(3, "Notas", "RECORTE L")        # igual: não conta
    for _ in range(3):
        assert grelha.undo()
    assert [(r.original_row, dict(r.values), r.removed) for r in grelha.rows] == antes
    assert not grelha.undo()
    # Uma operação nova depois de anular apaga o «refazer».
    grelha.delete_rows([1])
    assert not grelha.can_redo()


def test_dialogo_ctrl_z(app, grelha):
    dialogo = GrelhaListagemDialog(grelha)
    try:
        assert dialogo.actions["undo"].shortcut().toString() == "Ctrl+Z"
        grelha.copy_rows([0])
        dialogo.view.setCurrentIndex(dialogo.proxy.index(0, 2))
        dialogo.paste(after=True)
        assert dialogo.model.rowCount() == 5
        dialogo.undo()
        assert dialogo.model.rowCount() == 4
        assert "anulada" in dialogo.summary.text()
    finally:
        dialogo.close()
