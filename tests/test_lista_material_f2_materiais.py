"""F2 da Lista Material: referências das placas, decisões e pedido ao Woodstore.

Casos reais: obra 26.1610_01_01_JF_VIVA (21-09-2026) e as refs M6305/M6307 que
o Paulo deu como exemplo de troca fácil no IMOS. No Woodstore existem mesmo
`AGL_MLM_SMART_M6305/FLOW_19MM` e `AGL_MLM_SMART_M6305/FLW_19MM`.
"""
from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest
from openpyxl import Workbook
from PySide6.QtWidgets import QApplication

from app.domain import referencias_placa as refs
from app.services import analise_lista_material_service as svc
from app.services import lista_material_decisoes_service as decisoes
from app.services import pedido_material_woodstore_pdf as pedido
from app.services import verificacao_pre_cutrite_service as verificacao
from app.ui.dialogs import analise_lista_material_dialog as ui

MATERIAIS_USADOS_1610 = (
    "AGL_MLM_LINHO_CANCUN_10/16/19MM\n"
    "MDF_HID_BRANCO_B3002/MA_19MM\n"
    "AGL_MLM_BRANCO_B3768/SC_12/19MM"
)


def test_referencias_ignoram_espessuras_e_acabamentos():
    assert refs.referencias("AGL_MLM_BRANCO_B3768/SC_19MM") == {"B3768"}
    assert refs.referencias("AGL_MLM_ACACIA_LAKELAND_H1277/ST19_30MM") == {"H1277"}
    assert refs.referencias("AGL_MLM_LINHO_CANCUN_19MM") == set()
    assert refs.espessura("AGL_MLM_SMART_M6305/FLW_19MM") == 19


@pytest.mark.parametrize("a,b,esperado", [
    ("M6305", "M6307", True),
    ("H3710", "H3170", True),   # dois algarismos vizinhos trocados
    ("B3768", "B3002", False),
    ("M6305", "M6305", False),
    ("U708", "U7080", False),
])
def test_referencias_parecidas(a, b, esperado):
    assert refs.parecidas(a, b) is esperado


def test_obra_1610_contra_materias_usados():
    ok = refs.comparar_com_materiais_usados("MDF_MR_MLM_BRANCO_B3002/MA_19MM", MATERIAIS_USADOS_1610)
    assert ok.nivel == refs.OK
    sem_ref = refs.comparar_com_materiais_usados("AGL_MLM_LINHO_CANCUN_19MM", MATERIAIS_USADOS_1610)
    assert sem_ref.nivel == refs.OK
    tampo = refs.comparar_com_materiais_usados("Tampo PostForming_30mm", MATERIAIS_USADOS_1610)
    assert tampo.nivel == refs.AVISO


def test_ref_parecida_nas_materias_usados_e_alerta():
    resultado = refs.comparar_com_materiais_usados(
        "AGL_MLM_SMART_M6305/FLW_19MM", "Interiores AGL SMART M6307 19mm")
    assert resultado.nivel == refs.ALERTA
    assert resultado.sugeridas == ("M6307",)
    assert "M6307" in resultado.mensagem


def test_ref_diferente_sem_parecida_e_so_aviso():
    resultado = refs.comparar_com_materiais_usados("AGL_MLM_BRANCO_B3768/SC_19MM", "Carvalho H3710")
    assert resultado.nivel == refs.AVISO
    assert "H3710" in resultado.mensagem


def test_campo_vazio_nao_compara():
    assert refs.comparar_com_materiais_usados("AGL_MLM_BRANCO_B3768/SC_19MM", "  ").nivel == refs.INFO


def test_refs_das_materias_usados_que_nenhuma_peca_usa():
    lista = ["AGL_MLM_BRANCO_B3768/SC_19MM"]
    assert refs.referencias_esquecidas(lista, "B3768 e H3710") == ["H3710"]


def test_mesma_referencia_escrita_de_outra_forma_no_woodstore():
    codigos = ["AGL_MLM_SMART_M6305/FLOW_19MM", "AGL_MLM_SMART_M6305/FLW_19MM",
               "AGL_MLM_SMART_M6307/FLW_19MM", "AGL_MLM_SMART_M6305/FLW_10MM"]
    assert refs.mesma_referencia_no_woodstore("AGL_MLM_SMART_M6305_19MM", codigos) == [
        "AGL_MLM_SMART_M6305/FLOW_19MM", "AGL_MLM_SMART_M6305/FLW_19MM"]
    assert refs.vizinhas_no_woodstore("AGL_MLM_SMART_M6305/FLW_19MM", codigos) == [
        "AGL_MLM_SMART_M6307/FLW_19MM"]


def test_decisoes_gravadas_ao_lado_das_analises_sem_as_baralhar(tmp_path):
    livro = tmp_path / "Lista_Material_1610_01_26_JF_VIVA.xlsm"
    decisoes.gravar(livro, {"Tampo PostForming_30mm": {"acao": decisoes.FORA_CUTRITE}}, utilizador="paulo")
    decisoes.gravar(livro, {"TEMP_X": {"acao": decisoes.TEMPORARIO, "original": "X"}}, utilizador="paulo")

    lidas = decisoes.ler(livro)
    assert lidas["Tampo PostForming_30mm"]["acao"] == decisoes.FORA_CUTRITE
    assert lidas["TEMP_X"]["utilizador"] == "paulo"
    assert decisoes.descricao(lidas["TEMP_X"]) == "Nome temporário (em vez de X)"
    # Numa subpasta: o latest_snapshot das análises de custo não as lê.
    assert not list((tmp_path / "Analise_Lista_Material").glob("*.json"))
    with pytest.raises(ValueError):
        decisoes.gravar(livro, {"Y": {"acao": "apagar"}}, utilizador="paulo")


def test_verificacao_cutrite_nao_volta_a_avisar_o_que_foi_decidido():
    linhas = [
        {"Descricao": "Tampo", "Material": "Tampo PostForming_30mm", "Qt": 1},
        {"Descricao": "Teto", "Material": "AGL", "Qt": 2},
    ]
    resultado = verificacao.verificar(
        linhas, {"AGL"}, decisoes={"Tampo PostForming_30mm": "Fora do Cut-Rite"})

    assert resultado.tudo_certo
    assert resultado.materiais_decididos[0].pecas == 1
    assert "Fora do Cut-Rite" in verificacao.resumo_decididos(resultado)


def test_resumo_do_material_para_o_pedido():
    linhas = [
        {"Descricao": "Tampo", "Comp": 1475, "Larg": 620, "Qt": 1, "Esp": 30.2, "Veio": "N",
         "Orla ESQ": "PVC_1.0_BRANCO", "Orla DIR": "CNC_FRESAR"},
        {"Descricao": "Tampo", "Comp": 900, "Larg": 700, "Qt": 2, "Esp": 30.2},
    ]
    m = pedido.resumir_material("Tampo PostForming_30mm", linhas, ["AGL_MLM_BRANCO_B3768/SC_30MM"])
    assert (m.pecas, m.linhas) == (3, 2)
    assert (m.maior_comp, m.maior_larg) == (Decimal("1475"), Decimal("700"))
    assert m.area_m2 == Decimal("2.17")  # 0,9145 + 2 × 0,63
    assert m.orlas == ["PVC_1.0_BRANCO"]  # CNC_FRESAR é operação, não orla
    assert m.espessuras == ["30"]


@pytest.mark.skipif(not pedido.REPORTLAB_DISPONIVEL, reason="reportlab não instalado")
def test_pdf_do_pedido(tmp_path):
    m = pedido.resumir_material("Tampo PostForming_30mm", [{"Comp": 1475, "Larg": 620, "Qt": 1}])
    destino = pedido.gerar_pedido_pdf(tmp_path / "p.pdf", obra={"processo": "26.1610_01_01_JF_VIVA"},
                                      materiais=[m], gerado_em="21-09-2026", pedido_por="paulo")
    assert destino.read_bytes().startswith(b"%PDF")


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def livro(tmp_path):
    caminho = tmp_path / "Lista_Material_1610_01_26_JF_VIVA.xlsx"
    w = Workbook()
    w.active.title = "LISTAGEM_CUT_RITE"
    w.active.append(["Title"])
    w.active.append(["Descricao", "Material", "Comp", "Larg", "Qt", "Esp"])
    w.active.append(["Tampo", "Tampo PostForming_30mm", 1475, 620, 1, 30.2])
    w.active.append(["Lateral", "AGL_MLM_SMART_M6305/FLW_19MM", 2400, 600, 2, 19.2])
    w.save(caminho)
    return caminho


def _dialogo(session, livro, monkeypatch, usados=""):
    monkeypatch.setattr(ui, "query_woodstore", lambda _: [
        {"Codigo": "AGL_MLM_SMART_M6305/FLW_19MM", "Espessura": 19},
        {"Codigo": "AGL_MLM_SMART_M6307/FLW_19MM", "Espessura": 19},
        {"Codigo": "AGL_MLM_BRANCO_B3768/SC_30MM", "Espessura": 30},
    ])
    return ui.AnaliseListaMaterialDialog(
        session, workbook_path=livro, plan_name="1610_01_01_26_JF_VIVA",
        cutrite_folder=livro.parent, user=SimpleNamespace(role="admin", username="paulo"),
        materiais_usados=usados, obra_info={"processo": "26.1610_01_01_JF_VIVA"})


def _linha(dialogo, material):
    return next(i for i in range(dialogo.material_table.rowCount())
                if dialogo.material_table.item(i, 0).text() == material)


def test_alerta_de_referencia_e_codigo_sugerido(app, session, livro, monkeypatch):
    dialogo = _dialogo(session, livro, monkeypatch, usados="Interiores SMART M6307 19mm")
    try:
        i = _linha(dialogo, "AGL_MLM_SMART_M6305/FLW_19MM")
        assert "M6307" in dialogo.material_table.item(i, 7).text()
        combo = dialogo.choices["AGL_MLM_SMART_M6305/FLW_19MM"]
        codigos = [(combo.itemData(k) or {}).get("code") for k in range(combo.count())]
        assert "AGL_MLM_SMART_M6307/FLW_19MM" in codigos
        assert "1 com referência a confirmar" in dialogo.material_summary.text()
    finally:
        dialogo.close()


def test_decidir_fora_do_cutrite_fica_registado(app, session, livro, monkeypatch):
    dialogo = _dialogo(session, livro, monkeypatch)
    try:
        combo = dialogo.choices["Tampo PostForming_30mm"]
        combo.setCurrentIndex(next(k for k in range(combo.count())
                                   if (combo.itemData(k) or {}).get("acao") == decisoes.FORA_CUTRITE))
        dialogo._apply()
        assert decisoes.ler(livro)["Tampo PostForming_30mm"]["acao"] == decisoes.FORA_CUTRITE
        i = _linha(dialogo, "Tampo PostForming_30mm")
        assert "decidido: Fora do Cut-Rite" in dialogo.material_table.item(i, 2).text()
        assert "0 por decidir" in dialogo.material_summary.text()
    finally:
        dialogo.close()


@pytest.mark.skipif(not pedido.REPORTLAB_DISPONIVEL, reason="reportlab não instalado")
def test_pedido_pdf_regista_a_decisao(app, session, livro, monkeypatch):
    monkeypatch.setattr(ui.QDesktopServices, "openUrl", lambda *_: True)
    dialogo = _dialogo(session, livro, monkeypatch)
    try:
        dialogo._pedido_pdf()
        assert "Escolha «Pedir criação" in dialogo.status.text()
        combo = dialogo.choices["Tampo PostForming_30mm"]
        combo.setCurrentIndex(next(k for k in range(combo.count())
                                   if (combo.itemData(k) or {}).get("acao") == decisoes.CRIAR_WOODSTORE))
        dialogo._pedido_pdf()
        assert (livro.parent / "Pedido_Material_Woodstore_1610_01_26_JF_VIVA.pdf").is_file()
        assert decisoes.ler(livro)["Tampo PostForming_30mm"]["acao"] == decisoes.CRIAR_WOODSTORE
    finally:
        dialogo.close()


def test_snapshot_de_custos_ignora_a_pasta_das_decisoes(tmp_path):
    livro = tmp_path / "Lista_Material_1610_01_26_JF_VIVA.xlsm"
    livro.write_bytes(b"x")
    decisoes.gravar(livro, {"A": {"acao": decisoes.FORA_CUTRITE}}, utilizador="p")
    assert svc.latest_snapshot(livro, "1610_01_26_JF_VIVA") == {}
