"""Lista Material com a coluna «Colar» (modelo de ensaio, 06-11-2026): o lado do Martelo.

A coluna fica logo a seguir à CNC_2 e empurra +comp, +Larg, Esp.Mat, Esp.Final e
Tipo_Lacagem uma coluna para a direita. O que lê a LISTAGEM_CUT_RITE pela posição tem
de dar o mesmo no modelo de sempre e o certo no de ensaio.
"""

from __future__ import annotations

import inspect
from types import SimpleNamespace

import pytest
from openpyxl import Workbook

from app.services import cutrite_service as cutrite
from app.services import verificacao_pre_cutrite_service as verificacao

CABECALHO_SEMPRE = [
    "Descricao", "Material", "Comp", "Larg", "Qt", "Veio", "Orla", "Cliente",
    "Ref_Cliente", "Processo", "Artigo", "Notas", "Esp", "Grafico Orlas", "Orla ESQ",
    "Orla DIR", "Orla CIMA", "Orla BAIXO", "ID", "CNC_1", "CNC_2", "+comp\n", "+Larg",
    "Esp.Mat", "Esp.Final", "Tipo_Lacagem",
]
CABECALHO_COLAR = CABECALHO_SEMPRE[:21] + ["Colar"] + CABECALHO_SEMPRE[21:]


def _linha(ident, colar=None, *, com_colar=True, comp_extra=5, larg_extra=6):
    base = ["Tampo", "AGL_19MM", 900, 500, 1, "N", "", "CLI", "REF", "1608_03",
            "RP_01", "nota", 38, "x", "PVC", "", "", "", ident, "10001", "",
            comp_extra, larg_extra, 19, 38, ""]
    if com_colar:
        base.insert(21, colar)
    return base


def _livro(tmp_path, cabecalho, linhas, nome="Lista_Material_TESTE.xlsx"):
    livro = Workbook()
    folha = livro.active
    folha.title = "LISTAGEM_CUT_RITE"
    folha.append([None] * len(cabecalho))
    folha.append(cabecalho)
    for linha in linhas:
        folha.append(linha)
    caminho = tmp_path / nome
    livro.save(caminho)
    return caminho


# ---- Enviar CUT-RITE -------------------------------------------------------


def test_numero_de_colunas_para_o_cutrite():
    assert cutrite.cutrite_export_column_count(CABECALHO_SEMPRE) == 23
    assert cutrite.cutrite_export_column_count(CABECALHO_COLAR) == 24
    mal = CABECALHO_SEMPRE[:23] + ["Colar"] + CABECALHO_SEMPRE[23:]
    with pytest.raises(ValueError, match="logo a seguir à CNC_2"):
        cutrite.cutrite_export_column_count(mal)


def _colado(tmp_path, cabecalho, linhas):
    caminho = _livro(tmp_path, cabecalho, linhas)
    contexto = SimpleNamespace(source_workbook_path=caminho, import_workbook_path=tmp_path / "x.xls")
    _, export, texto = cutrite.build_cutrite_import_workbook(contexto)
    return export, [ln.split("\t") for ln in texto.split("\r\n")]


def test_modelo_de_sempre_manda_as_23_colunas_de_hoje(tmp_path):
    export, colado = _colado(tmp_path, CABECALHO_SEMPRE, [_linha(1, com_colar=False)])
    assert len(export[0]) == 23 and len(colado[0]) == 23
    assert colado[0][20:23] == ["", "5", "6"]  # CNC_2, +comp, +Larg
    assert colado[0][13] == cutrite.CUTRITE_GRAFICO_ORLAS_VALUE


def test_modelo_com_colar_manda_24_colunas_com_a_colar_a_seguir_a_cnc2(tmp_path):
    export, colado = _colado(tmp_path, CABECALHO_COLAR, [_linha(14, "14+14_O4L")])
    assert len(export[0]) == 24 and len(colado[0]) == 24
    assert colado[0][18:24] == ["14", "10001", "", "14+14_O4L", "5", "6"]


# ---- Verificação antes do Cut-Rite ---------------------------------------


def test_verificacao_le_a_colar_e_o_mais_larg_no_sitio_certo(tmp_path):
    caminho = _livro(tmp_path, CABECALHO_COLAR, [_linha(1, "1+2"), _linha(2, "1+2")])
    linhas = verificacao.ler_linhas(caminho)
    assert linhas[0]["Colar"] == "1+2"
    assert linhas[0]["+Larg"] == 6
    assert "Esp.Mat" not in linhas[0]
    resultado = verificacao.verificar(linhas, {"AGL_19MM"})
    assert resultado.colar_problemas == []
    assert resultado.tudo_certo


def test_verificacao_avisa_dos_codigos_desencontrados(tmp_path):
    caminho = _livro(tmp_path, CABECALHO_COLAR, [_linha(1, "1+2_O4L"), _linha(2, ""), _linha(3, "3 +4")])
    resultado = verificacao.verificar(verificacao.ler_linhas(caminho), {"AGL_19MM"})
    assert not resultado.tudo_certo
    texto = verificacao.texto_do_aviso(resultado)
    assert "COLUNA COLAR" in texto
    assert "a linha ID 2 tem outro código (vazio)" in texto
    assert "tem espaços" in texto


def test_verificacao_do_modelo_de_sempre_nao_fala_da_colar(tmp_path):
    caminho = _livro(tmp_path, CABECALHO_SEMPRE, [_linha(1, com_colar=False)])
    linhas = verificacao.ler_linhas(caminho)
    assert "Colar" not in linhas[0] and len(linhas[0]) == 23
    assert verificacao.verificar(linhas, {"AGL_19MM"}).colar_problemas == []


def test_envio_mostra_a_caixa_quando_so_ha_problemas_na_colar():
    from app.ui.pages.producao_page import ProducaoPage

    fonte = inspect.getsource(ProducaoPage)
    assert "and not resultado.colar_problemas" in fonte


# ---- Lacagem e camada do assistente -----------------------------------------


def test_lacagem_liga_ao_tipo_lacagem_na_z_ou_na_aa():
    from app.services.lista_material_acabamentos_service import _ORIGEM_TIPO

    sempre = '=IF(NOT(LISTAGEM_CUT_RITE!X7=""),LISTAGEM_CUT_RITE!Z7,"")'
    colar = '=IF(NOT(LISTAGEM_CUT_RITE!Y7=""),LISTAGEM_CUT_RITE!AA7,"")'
    assert _ORIGEM_TIPO.search(sempre).group(1) == "7"
    assert _ORIGEM_TIPO.search(colar).group(1) == "7"


def test_sourceid_vai_para_a_coluna_a_seguir_a_tabela():
    from app.services.lista_material_assistente_service import _coluna_depois_da_tabela

    def folha(coluna, colunas, cabecalhos=None):
        cabecalhos = cabecalhos or {}
        tabela = SimpleNamespace(Range=SimpleNamespace(Column=coluna, Columns=SimpleNamespace(Count=colunas)))
        celulas = SimpleNamespace(Item=lambda linha, col: SimpleNamespace(Value=cabecalhos.get(col)))
        return SimpleNamespace(ListObjects=SimpleNamespace(Item=lambda nome: tabela), Cells=celulas)

    assert _coluna_depois_da_tabela(folha(1, 26)) == 27  # A:Z -> AA
    assert _coluna_depois_da_tabela(folha(1, 27)) == 28  # A:AA (com Colar) -> AB
    # A tabela engoliu o SourceID que o Martelo pôs ao lado dela: fica onde está.
    assert _coluna_depois_da_tabela(folha(1, 28, {27: "SourceID", 28: "Estado_Assistente"})) == 27
    assert _coluna_depois_da_tabela(folha(1, 29, {28: "SourceID"})) == 28

    def sem_tabela(nome):
        raise KeyError(nome)

    vazia = SimpleNamespace(Item=lambda linha, col: SimpleNamespace(Value=None))
    assert _coluna_depois_da_tabela(
        SimpleNamespace(ListObjects=SimpleNamespace(Item=sem_tabela), Cells=vazia)
    ) == 27


# ---- Martelo: opção nas Funções -------------------------------------------


def test_opcao_lista_com_colar_nas_funcoes():
    from app.ui.pages.producao_page import ProducaoPage

    init = inspect.getsource(ProducaoPage.__init__)
    assert '"Lista Material com coluna Colar (ensaio)…", self' in init
    assert "self.lista_colar_action.setToolTip(" in init
    assert "self._lista_material_imos(modelo=TEMPLATE_FILENAME_COLAR)" in init
    assert "self.funcoes_menu.addAction(self.lista_colar_action)" in init
    # O botão de sempre continua no modelo de sempre.
    assert "self.lista_material_button.clicked.connect(self._lista_material_imos)" in init
    fluxo = inspect.getsource(ProducaoPage._lista_material_imos)
    assert fluxo.count("template_filename=modelo") == 2


def test_botao_de_sempre_ignora_o_checked_do_clicked():
    from app.ui.pages.producao_page import ProducaoPage

    assinatura = inspect.signature(ProducaoPage._lista_material_imos)
    modelo = assinatura.parameters["modelo"]
    assert modelo.kind is inspect.Parameter.KEYWORD_ONLY
    assert modelo.default == "Lista_Material_IMOS_MARTELO.xltm"


def test_modelo_colar_pelo_nome(session, tmp_path):
    from app.models.producao import Producao
    from app.repositories.system_setting_repository import SystemSettingRepository
    from app.services.lista_material_imos_service import (
        KEY_PASTA_BASE_DADOS_ORCAMENTO,
        TEMPLATE_FILENAME_COLAR,
        prepare_lista_material_imos,
    )

    pasta = tmp_path / "obra"
    pasta.mkdir()
    base = tmp_path / "base"
    base.mkdir()
    (base / TEMPLATE_FILENAME_COLAR).write_text("x")
    session.add(Producao(id=1, codigo_processo="26.1608_03_01_HIRONDELLES", ano="2026",
                         num_enc_phc="1608", versao_obra="03", versao_plano="01",
                         pasta_servidor=str(pasta)))
    SystemSettingRepository(session).upsert_setting(
        chave=KEY_PASTA_BASE_DADOS_ORCAMENTO, valor=str(base),
        descricao="Pasta Base Dados Orcamento", tipo="pasta", grupo="Orcamentos",
    )
    session.commit()

    ctx = prepare_lista_material_imos(session, processo_id=1, nome_enc_imos="1608_03_26_HIRONDELLES",
                                      values={}, template_filename=TEMPLATE_FILENAME_COLAR)
    assert ctx.template_path == base / TEMPLATE_FILENAME_COLAR
    assert ctx.output_path.name == "Lista_Material_1608_03_26_HIRONDELLES.xlsm"
