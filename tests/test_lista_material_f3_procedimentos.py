"""F3 da Lista Material: procedimentos da LISTAGEM_CUT_RITE religados.

Casos reais das obras lowcost 1568/1562/1582 (JF_VIVA, 14 e 15-09-2026),
comparando a cópia de antes das ferragens com a lista final:
* nota das costas = piso/fração do artigo («RP_13_P1_F» → «PISO 1º - F»);
* notas em maiúsculas («LACAR 1 FACE + PUX TIC-TAC», «NÃO LACAR»);
* troca de orla em massa (1562: ~400 células PVC_0.4_LINHO → PVC_1.0_LINHO);
* a orla aprendida estava guardada normalizada (PVC_0_4_LINHO) e ia assim para o Excel.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from openpyxl import Workbook
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from app.models.lista_material_assistente import ListaMaterialRelacaoOrla
from app.services.lista_material_assistente_service import (
    AssistantConfig, AssistantSuggestion, ListaMaterialAssistantService, MaterialRow,
    edge_replacement_suggestions, localizacao_do_artigo, read_material_table, rule_group,
)
from app.ui.dialogs import procedimentos_lista_material_widget as proc


def _row(n=3, description="Costa", article="RP_01", edges=None, notes="", material="AGL_MLM_LINHO_CANCUN_19MM"):
    return MaterialRow(
        row_number=n, source_id=f"S{n}", description=description, material=material,
        length=Decimal("2400"), width=Decimal("500"), quantity=Decimal("1"),
        article=article, notes=notes,
        edges=edges or {"Orla ESQ": "", "Orla DIR": "", "Orla CIMA": "", "Orla BAIXO": ""},
    )


@pytest.mark.parametrize("artigo,esperado", [
    ("RP_13_P1_F", "PISO 1º - F"),
    ("RP_18_RC_A", "RES DO CHAO - A"),
    ("RP_B_05_RC_ESQ", "RES DO CHAO ESQUERDO"),
    ("RP_C_06_P1_DIR", "PISO 1º DIREITO"),
    ("RP_E_14_P2_DIR", "PISO 2º DIREITO"),
    ("RP_A_01", ""),
    ("RP_A_05(a)", ""),
])
def test_localizacao_do_artigo(artigo, esperado):
    assert localizacao_do_artigo(artigo) == esperado


def test_costa_recebe_o_piso_e_nao_a_nota_cnc(session):
    rows = [
        _row(3, "Costa", "RP_13_P1_F"),
        _row(4, "Costa Canto Recorte", "RP_02_P2_L",
             edges={"Orla ESQ": "CNC_FRESAR", "Orla DIR": "", "Orla CIMA": "", "Orla BAIXO": ""}),
        _row(5, "Costa", "RP_18_RC_A", notes="PISO RES DO CHAO - A"),
    ]
    config = AssistantConfig(user_id=7, client="JF_VIVA", cnc_note="CNC RECORTE L")
    notas = {s.row_number: s for s in ListaMaterialAssistantService(session).analyze_rows(rows, config=config)
             if s.field == "Notas"}
    assert notas[3].suggested == "PISO 1º - F"
    assert notas[3].kind == "notas_localizacao"
    assert notas[4].suggested == "PISO 2º - L"
    assert 5 not in notas  # já lá está


def test_orla_aprendida_volta_ao_nome_real(session):
    session.add(ListaMaterialRelacaoOrla(
        material_normalizado="AGL_MLM_LINHO_CANCUN_19MM", orla_normalizada="PVC_0_4_LINHO",
        user_id=0, cliente_chave="", origem="teste", estado="aprovado",
        confianca=Decimal("0.9"), suporte=64))
    session.flush()
    maleiro = _row(3, "Maleiro", edges={"Orla ESQ": "PVC_1.0_LINHO", "Orla DIR": "CNC_FRESAR",
                                        "Orla CIMA": "CNC_FRESAR", "Orla BAIXO": ""})
    outra = _row(4, "Teto", edges={"Orla ESQ": "PVC_0.4_LINHO", "Orla DIR": "", "Orla CIMA": "", "Orla BAIXO": ""})
    config = AssistantConfig(user_id=7, client="JF_VIVA")
    service = ListaMaterialAssistantService(session)

    com_nome = [s for s in service.analyze_rows([maleiro, outra], config=config) if s.kind == "cnc_fresar"]
    assert {s.suggested for s in com_nome} == {"PVC_0.4_LINHO"}

    # Sem a orla escrita em lado nenhum da lista, não se inventa um nome.
    sem_nome = [s for s in ListaMaterialAssistantService(session).analyze_rows([maleiro], config=config)
                if s.kind == "cnc_fresar"]
    assert all(s.suggested == "" and s.blocking for s in sem_nome)


def test_orla_em_massa_respeita_lados_e_pecas():
    rows = [
        _row(3, "Teto", edges={"Orla ESQ": "PVC_0.4_LINHO", "Orla DIR": "PVC_0.4_LINHO", "Orla CIMA": "", "Orla BAIXO": ""}),
        _row(4, "Frente de gaveta", edges={"Orla ESQ": "PVC_0.4_LINHO", "Orla DIR": "PVC_0.4_LINHO",
                                            "Orla CIMA": "PVC_0.4_LINHO", "Orla BAIXO": "PVC_0.4_LINHO"}),
    ]
    todas = edge_replacement_suggestions(rows, origem="PVC_0.4_LINHO", destino="PVC_1.0_LINHO")
    assert len(todas) == 6
    so_esq = edge_replacement_suggestions(rows, origem="PVC_0.4_LINHO", destino="PVC_1.0_LINHO",
                                          lados=("Orla ESQ",), descricoes=("Teto",))
    assert [(s.row_number, s.field, s.suggested) for s in so_esq] == [(3, "Orla ESQ", "PVC_1.0_LINHO")]
    assert rule_group(so_esq[0].kind) == "Substituição de orla"
    assert edge_replacement_suggestions(rows, origem="X", destino="X") == []


def _sug(row, field, value, kind="notas_assistente", blocking=False, delete=False):
    return AssistantSuggestion(source_id=f"S{row}", row_number=row, field=field, original="",
                               suggested=value, reason="", confidence=0.9, kind=kind,
                               blocking=blocking, delete_row=delete)


def test_aceitar_em_bloco_salta_bloqueios_e_celulas_repetidas():
    grupos = proc.group_suggestions([
        _sug(3, "Notas", "PUX TIC-TAC"),
        _sug(4, "Orla DIR", "", kind="cnc_fresar", blocking=True),
        _sug(5, "Orla ESQ", "PVC_1.0_BRANCO", kind="remate_teto_lacagem"),
        _sug(5, "Orla ESQ", "PVC_1.0_LINHO", kind="orla_em_massa"),
        _sug(6, "__DELETE_ROW__", "", kind="barra_rodape_frente_short_remover_linha", delete=True),
    ])
    todos = {label for label, _ in grupos}
    decisoes, saltadas = proc.accepted_decisions(grupos, todos)
    assert [(d.suggestion.row_number, d.suggestion.field) for d in decisoes] == [
        (3, "Notas"), (5, "Orla ESQ"), (6, "__DELETE_ROW__")]
    assert saltadas == 1
    assert "Substituição de orla: " in " ".join(todos)


def test_leitura_rapida_da_listagem(tmp_path):
    caminho = tmp_path / "Lista_Material_1568_01_26_JF_VIVA.xlsx"
    w = Workbook()
    w.active.title = "LISTAGEM_CUT_RITE"
    w.active.append(["Title"])
    w.active.append(["Descricao", "Material", "Comp", "Larg", "Qt", "Artigo", "Notas",
                     "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO", "ID"])
    for i in range(800):
        w.active.append(["Costa", "AGL_MLM_LINHO_CANCUN_10MM", 2400, 500, 1, "RP_13_P1_F", None,
                         None, None, None, None, 1000 + i])
    w.save(caminho)
    colunas, linhas = read_material_table(caminho)
    assert len(linhas) == 800
    assert linhas[0].row_number == 3 and linhas[0].source_id == "1000"
    assert linhas[-1].article == "RP_13_P1_F"
    assert "Orla ESQ" in colunas


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


def test_separador_agrupa_por_regra_e_junta_a_orla_em_massa(app, session, tmp_path):
    caminho = tmp_path / "Lista_Material_1568_01_26_JF_VIVA.xlsx"
    w = Workbook()
    w.active.title = "LISTAGEM_CUT_RITE"
    w.active.append(["Title"])
    w.active.append(["Descricao", "Material", "Comp", "Larg", "Qt", "Artigo", "Notas",
                     "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO", "ID"])
    w.active.append(["Costa", "AGL_MLM_LINHO_CANCUN_10MM", 2400, 500, 1, "RP_13_P1_F", None,
                     None, None, None, None, 1])
    w.active.append(["Porta direita", "AGL_MLM_LINHO_CANCUN_19MM", 2400, 500, 1, "RP_13_P1_F", None,
                     "PVC_0.4_LINHO", "PVC_0.4_LINHO", None, None, 2])
    w.save(caminho)
    widget = proc.ProcedimentosListaMaterialWidget(
        session, user=SimpleNamespace(id=0, username="paulo"),
        permissions={"acao.corrigir_lista_material": True}, workbook_path=caminho,
        obra_info={"cliente": "JF_VIVA", "descricao_producao": "Puxador TIC-TAC"},
        catalog_provider=lambda: [], on_applied=lambda: None)
    try:
        widget.analyse()
        regras = [label for label, _ in widget.groups]
        assert "Notas das costas: piso/fração do artigo" in regras
        widget.bulk_specs.append({"origem": "PVC_0.4_LINHO", "destino": "PVC_1.0_LINHO"})
        widget.analyse()
        regras = [label for label, _ in widget.groups]
        assert "Substituição de orla: PVC_0.4_LINHO → PVC_1.0_LINHO" in regras
        assert widget.table.item(0, 0).checkState() == Qt.CheckState.Checked
        assert "peças analisadas" in widget.status.text()
    finally:
        widget.close()


def test_dialogo_orla_em_massa_conta_as_celulas(app):
    rows = [_row(3, "Teto", edges={"Orla ESQ": "PVC_0.4_LINHO", "Orla DIR": "PVC_0.4_LINHO",
                                   "Orla CIMA": "CNC_FRESAR", "Orla BAIXO": ""})]
    dialogo = proc.OrlaEmMassaDialog(rows)
    try:
        assert dialogo.origem.findData("CNC_FRESAR") == -1  # operação, não orla
        dialogo.destino.setCurrentText("PVC_1.0_LINHO")
        assert dialogo.spec()["destino"] == "PVC_1.0_LINHO"
        assert dialogo.preview.text().startswith("2 células em 1 peças")
        dialogo.sides["Orla DIR"].setChecked(False)
        assert dialogo.preview.text().startswith("1 células")
    finally:
        dialogo.close()
