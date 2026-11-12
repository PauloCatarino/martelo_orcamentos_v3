"""Guarda as macros do modelo de ensaio COLAR (fonte em scripts/vba/colar).

O modelo ``Lista_Material_IMOS_MARTELO_COLAR.xltm`` é criado por
``scripts/criar_modelo_lista_material_colar.py`` a partir do de sempre, que não muda.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from app.domain import codigo_colar
from app.services.lista_material_imos_service import TEMPLATE_FILENAME_COLAR

RAIZ = Path(__file__).resolve().parents[1]
VBA = RAIZ / "scripts" / "vba"
COLAR = VBA / "colar"


def _ler(caminho: Path) -> str:
    bruto = caminho.read_bytes()
    assert b"\r\n" in bruto and b"\n" not in bruto.replace(b"\r\n", b""), caminho.name
    return bruto.decode("cp1252")


def _script(nome: str):
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "scripts" / f"{nome}.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def test_modcolar_tem_as_macros_dos_botoes_e_as_regras():
    codigo = _ler(COLAR / "modColar.bas")
    for assinatura in (
        "Public Sub AbrirMenuColar()",
        "Public Sub VerificarCodigosColar()",
        "Public Function ColarMontar(",
        "Public Function ColarLer(",
        "Public Function ColarGravar(",
        "Public Function ColarProblemas(",
        "Public Function ColarCelulaDaColuna(",
    ):
        assert assinatura in codigo
    # As mesmas orlas que o Martelo aceita.
    for orla in codigo_colar.ORLAS:
        assert f'"{orla}"' in codigo
    # Duas peças do mesmo ID sozinhas: 14+14 (decisão do Paulo, 06-11-2026).
    assert 'ColarConjuntoTexto = k & "+" & k' in codigo
    assert 's = "O4L"' in codigo


def test_menu_cria_os_controlos_com_dicas_e_linha_de_estado():
    codigo = _ler(COLAR / "frmColar.vba")
    assert "Private Sub UserForm_Initialize()" in codigo
    assert codigo.count("Novo(\"Forms.") >= 14
    # Botões e campos com dica (tooltip), e a linha de estado por baixo dos botões.
    assert len(re.findall(r'Novo\("Forms\.(?:CommandButton|CheckBox|ComboBox|TextBox|ListBox)\.1", "\w+", [^)]*,\s*_?\s*"', codigo)) >= 1
    assert codigo.count("ControlTipText") >= 1
    assert 'Set lblEstado = Rotulo("lblEstado"' in codigo
    assert "msg = ColarGravar(mConj, cod, mCodigoAntigo, True, CBool(chkMudarQt.Value)," in codigo
    assert "problemas = ColarProblemas(15)" in codigo


def test_gravar_muda_a_qt_e_os_excedentes():
    codigo = _ler(COLAR / "modColar.bas")
    assert "Public Function ColarIndiceMais(" in codigo
    assert "Optional ByVal mudarQt As Boolean = False" in codigo
    # Qt = peças da linha no conjunto x nº de conjuntos (47+47 x 8 -> 16; 47+48 x 6 -> 6 e 6).
    assert "Optional ByVal conjuntos As Long = 1) As String" in codigo
    assert "lo.DataBodyRange.Cells(r, colQt).Value = CLng(conj(idTxt)) * conjuntos" in codigo
    assert "lo.DataBodyRange.Cells(r, colMaisComp).Value" in codigo
    assert "lo.DataBodyRange.Cells(r, colMaisLarg).Value" in codigo


def test_menu_2a_ronda_pesquisa_excedentes_tolerancia_e_arestas():
    codigo = _ler(COLAR / "frmColar.vba")
    assert 'Private Const EXCEDENTE_POR_DEFEITO As String = "20"' in codigo
    assert "Private Sub txtPesquisa_Change()" in codigo
    assert "PassaPesquisa(r)" in codigo
    assert "Private Const TOLERANCIA_MM As Double = 2" in codigo
    assert "(é a que manda)" in codigo
    for aresta in ("C1", "C2", "L1", "L2"):
        assert f"Private Sub lblAresta{aresta}_Click()" in codigo
    assert "ColarOrlasTexto(NComp(), NLarg(), chkRaio.Value)" in codigo
    assert "CBool(chkMudarQt.Value)" in codigo
    # O VBA não distingue maiúsculas: uma constante e uma função com o mesmo nome não compilam.
    nomes = re.findall(r"^(?:Private|Public) (?:Const|Function|Sub) (\w+)", codigo, re.MULTILINE)
    minusculas = [n.lower() for n in nomes]
    assert len(minusculas) == len(set(minusculas))


def test_menu_3a_ronda_conjuntos_desenho_da_linha_selecionada():
    codigo = _ler(COLAR / "frmColar.vba")
    assert "Private WithEvents txtConjuntos As MSForms.TextBox" in codigo
    assert "Trim$(txtMaisComp.Text), Trim$(txtMaisLarg.Text), NumConjuntos())" in codigo
    assert "Private Sub lstConjunto_Click()" in codigo
    assert "ident = IdDoDesenho()" in codigo
    assert "txtConjuntos.Text = CStr(ConjuntosDaLinha(r))" in codigo
    # Saíram: «Quantas de cada» e «Tirar o código destas peças».
    assert "Set txtQt" not in codigo and '"Quantas de cada:"' not in codigo
    assert "btnLimpar" not in codigo and '"Tirar o código destas peças"' not in codigo


def test_copia_listagem_do_colar_vai_ate_ao_mais_larg_e_confere_a_colar():
    codigo = _ler(COLAR / "Copia_List_Soft_Cut_Rite.bas")
    assert "colFim = ColunaMaisLarg(lo)" in codigo
    assert "problemas = ColarProblemas(10)" in codigo
    assert 'ws.Range("A3:W" & lastRow)' not in codigo
    assert 'If LCase$(nome) = "+larg" Then' in codigo
    # O modelo de sempre continua a copiar A3:W.
    sempre = _ler(VBA / "Copia_List_Soft_Cut_Rite.bas")
    assert 'Set rngCopy = ws.Range("A3:W" & lastRow)' in sempre
    assert "ColarProblemas" not in sempre


def test_duplo_clique_na_folha_e_o_resto_do_codigo_igual():
    codigo = _ler(COLAR / "Folha5_LISTAGEM_CUT_RITE.cls")
    assert "Private Sub Worksheet_BeforeDoubleClick(ByVal Target As Range, Cancel As Boolean)" in codigo
    assert "If ColarCelulaDaColuna(Target) Then" in codigo
    assert "Application.CalculateFull" in codigo  # o que já lá estava


def test_modelo_de_sempre_nao_recebe_os_modulos_do_colar():
    atualizar = _script("atualizar_macros_modelo_lista_material")
    for nome in ("modColar", "frmColar", "Copia_List_Soft_Cut_Rite"):
        assert nome not in atualizar.MODULOS


def test_script_do_modelo_colar():
    criar = _script("criar_modelo_lista_material_colar")
    assert criar.NOME_COLAR == TEMPLATE_FILENAME_COLAR
    assert criar.COLUNA == "Colar"
    for ficheiro, nome, _tipo in criar.MODULOS_COLAR:
        assert (COLAR / ficheiro).is_file()
        assert criar.MARCADORES[nome] in _ler(COLAR / ficheiro)
    assert (COLAR / criar.CODIGO_DA_FOLHA).is_file()
    assert len(criar.DICA_COLUNA) <= 255  # limite da mensagem de entrada do Excel


def test_colar_anterior_fica_guardado_com_a_data(tmp_path):
    criar = _script("criar_modelo_lista_material_colar")
    destino = tmp_path / TEMPLATE_FILENAME_COLAR
    assert criar.guardar_anterior(destino) is None
    destino.write_text("velho")
    anterior = criar.guardar_anterior(destino)
    assert anterior is not None and anterior.read_text() == "velho"
    assert anterior.name.startswith("Lista_Material_IMOS_MARTELO_COLAR_anterior_")
    assert not destino.exists()
