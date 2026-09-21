"""F0 da Lista Material: verificação antes do Cut-Rite, Excel sem #NAME? e Woodstore real.

Os dados vêm da obra 26.1610_01_01_JF_VIVA (21-09-2026): seis materiais
validados no Woodstore, o `Tampo PostForming_30mm` sem código, e Ref_Cliente /
Processo gravados como `#NAME?` depois de o Martelo importar as ferragens.
"""
from __future__ import annotations

import inspect
from decimal import Decimal

from openpyxl import Workbook

from app.services import analise_lista_material_service
from app.services import lista_material_assistente_service
from app.services import lista_material_excel_com as excel_com
from app.services import verificacao_pre_cutrite_service as verificacao
from app.services.warehouse_board_catalog import WoodstoreBoardCatalogProvider

CABECALHO = [
    "Descricao", "Material", "Comp", "Larg", "Qt", "Veio", "Orla", "Cliente",
    "Ref_Cliente", "Processo", "Artigo", "Notas", "Esp", "Grafico Orlas",
    "Orla ESQ", "Orla DIR", "Orla CIMA", "Orla BAIXO", "ID", "CNC_1", "CNC_2",
    "+comp\n", "+Larg", "Esp.Mat", "Esp.Final",
]


def _linha(descricao, material, qt, ref="2607010", processo="1610_01_01_26"):
    return {
        "Descricao": descricao, "Material": material, "Qt": qt,
        "Ref_Cliente": ref, "Processo": processo,
    }


def test_material_sem_codigo_no_woodstore_e_contado_por_pecas():
    linhas = [
        _linha("Lateral Esquerda", "AGL_MLM_LINHO_CANCUN_19MM", 2),
        _linha("Tampo", "Tampo PostForming_30mm", 1),
        _linha("Tampo", "Tampo PostForming_30mm", 2),
    ]

    resultado = verificacao.verificar(linhas, {"AGL_MLM_LINHO_CANCUN_19MM "})

    assert [m.material for m in resultado.materiais_em_falta] == ["Tampo PostForming_30mm"]
    em_falta = resultado.materiais_em_falta[0]
    assert (em_falta.pecas, em_falta.linhas, em_falta.descricoes) == (3, 2, ("Tampo",))
    assert not resultado.tudo_certo
    texto = verificacao.texto_do_aviso(resultado)
    assert "3 peça(s) NÃO vão ser cortadas" in texto
    assert "versão nova do plano" in texto
    assert "nome temporário" in texto


def test_celulas_com_erro_do_excel_sao_apanhadas_nas_duas_linguas():
    linhas = [
        _linha("Costa", "AGL", 1, ref="#NAME?", processo="#NAME?"),
        _linha("Costa", "AGL", 1, ref="#NOME?", processo="1610"),
    ]

    resultado = verificacao.verificar(linhas, {"AGL"})

    por_coluna = {c.coluna: c.linhas for c in resultado.colunas_com_erro}
    assert por_coluna == {"Ref_Cliente": 2, "Processo": 1}
    assert "Reparar e enviar" in verificacao.texto_do_aviso(resultado)
    assert "Reparar e enviar" not in verificacao.texto_do_aviso(resultado, pode_reparar=False)


def test_sem_woodstore_nao_inventa_materiais_em_falta():
    linhas = [_linha("Tampo", "Tampo PostForming_30mm", 1, ref="#NAME?")]

    resultado = verificacao.verificar(linhas, None, woodstore_aviso="Sem rede.")

    assert resultado.materiais_em_falta == []
    assert not resultado.woodstore_verificado
    assert resultado.woodstore_aviso == "Sem rede."
    # Os erros do Excel continuam a ser verificados sem o Woodstore.
    assert [c.coluna for c in resultado.colunas_com_erro] == ["Ref_Cliente"]


def test_tudo_certo_quando_os_materiais_existem():
    resultado = verificacao.verificar([_linha("Teto", "AGL", 2)], {"AGL"})
    assert resultado.tudo_certo
    assert verificacao.texto_do_aviso(resultado) == ""


def test_ler_linhas_so_as_colunas_que_vao_para_o_cutrite(tmp_path):
    livro = Workbook()
    folha = livro.active
    folha.title = "LISTAGEM_CUT_RITE"
    folha.append([None] * len(CABECALHO))
    folha.append(CABECALHO)
    folha.append(["Tampo", "Tampo PostForming_30mm", 1475, 620, 1] + [None] * 18 + ["#NAME?", "#NAME?"])
    folha.append([None] * len(CABECALHO))
    caminho = tmp_path / "Lista_Material_1610_01_26_JF_VIVA.xlsm"
    livro.save(caminho)

    linhas = verificacao.ler_linhas(caminho)

    assert len(linhas) == 1
    assert linhas[0]["Material"] == "Tampo PostForming_30mm"
    # Esp.Mat / Esp.Final não vão para o Cut-Rite: um #NAME? aí não é aviso.
    assert "Esp.Mat" not in linhas[0]
    assert verificacao.verificar(linhas, {"X"}).colunas_com_erro == []


def test_woodstore_provider_diz_a_verdade_sobre_a_ligacao():
    leituras = []

    def ler():
        leituras.append(1)
        return [
            {"Referencia": "FM00043", "Codigo": "AGL_MLM_LINHO_CANCUN_19MM",
             "Material": "AGL MLM LINHO CANCUN 2850X2100X19", "Comprimento": 2850,
             "Largura": 2100, "Espessura": 19, "Quantidade": 192, "Reservadas": 263,
             "Disponivel": -71},
            {"Referencia": "FM00436", "Codigo": "AGL_MLM_LINHO_CANCUN_19MM",
             "Material": "AGL MLM LINHO CANCUN 2440X2100X19", "Espessura": 19},
        ]

    provider = WoodstoreBoardCatalogProvider(ler)

    estado = provider.status()
    assert estado.available
    assert "2 placas, 1 materiais" in estado.message
    assert "ainda não configurada" not in estado.message
    placas = provider.list_boards()
    assert placas[0].thickness == Decimal("19")
    assert placas[0].available == Decimal("-71")
    assert len(leituras) == 1  # lê o Woodstore uma só vez


def test_woodstore_provider_sem_ligacao():
    def falha():
        raise RuntimeError("WoodStore sem ligação ou consulta recusada.")

    provider = WoodstoreBoardCatalogProvider(falha)

    estado = provider.status()
    assert not estado.available
    assert "sem ligação" in estado.message
    assert "ainda não configurada" not in estado.message
    assert provider.list_boards() == []


def test_excel_com_macros_ativas_e_eventos_desligados():
    class ExcelFalso:
        pass

    excel = ExcelFalso()
    excel_com.preparar_excel(excel)

    assert excel.AutomationSecurity == 1
    assert excel.EnableEvents is False
    assert excel.Visible is False


def test_gravacoes_do_martelo_nao_desligam_as_macros():
    """Com as macros desligadas o Excel grava #NAME? nas colunas com funções VBA."""
    for modulo in (analise_lista_material_service, lista_material_assistente_service):
        fonte = inspect.getsource(modulo)
        assert "AutomationSecurity = 3" not in fonte, modulo.__name__
        assert fonte.count("excel_com.preparar_excel(excel)") == fonte.count(
            "DispatchEx"
        ), modulo.__name__
