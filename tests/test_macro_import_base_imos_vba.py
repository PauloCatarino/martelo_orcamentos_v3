"""Guarda a importação da Lista Material (fonte em scripts/vba/modImportCSVImos_1.bas).

A ``Import_CSV_Imos_1`` (CSV exportado pelo iMos) fica como estava; a
``Import_Base_Imos_1`` (ensaio de 30-10-2026) faz os mesmos passos sobre o CSV
que o Martelo escreve a partir da base do iMos.
"""

from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MODULO = RAIZ / "scripts" / "vba" / "modImportCSVImos_1.bas"
SCRIPT = RAIZ / "scripts" / "atualizar_macros_modelo_lista_material.py"


def _codigo() -> str:
    return MODULO.read_bytes().decode("cp1252")


def _sub(nome: str) -> str:
    codigo = _codigo()
    inicio = codigo.index(f"Public Sub {nome}(")
    return codigo[inicio:codigo.index("End Sub", inicio)]


def test_ficheiro_em_cp1252_com_crlf() -> None:
    bruto = MODULO.read_bytes()
    assert b"\r\n" in bruto and b"\n" not in bruto.replace(b"\r\n", b"")
    assert _codigo().startswith('Attribute VB_Name = "modImportCSVImos_1"')


def test_importacao_normal_continua_a_procurar_o_csv_do_imos() -> None:
    normal = _sub("Import_CSV_Imos_1")
    assert r'Private Const PASTA_CSV As String = "I:\Cutrite\Work\Cutrite_Import_CSV\"' in _codigo()
    assert "caminhoCSV = EncontrarCSVPorProcesso(PASTA_CSV, numProcesso)" in normal
    assert "Import_Base_Imos_1" not in normal


def test_importacao_da_base_faz_os_mesmos_passos_com_o_ficheiro_dado() -> None:
    passos = (
        'RecriarFolhaImport(numProcesso, "LISTA_ORDENADA")',
        "LimparFolhaImport wsImport",
        'LimparListaOrdenada ThisWorkbook.Worksheets("LISTA_ORDENADA")',
        "ImportarCSV_ParaFolha wsImport, caminhoCSV",
        "Tratar_Linhas_Qt_Zero wsImport",
        "CorrigirColunaRP wsImport",
        "VerificarECorrigir_Rasgo_Em_Notas wsImport",
        "Criar_Lista_Ordenada wsImport,",
        'Converter_Veio_ListaOrdenada ThisWorkbook.Worksheets("LISTA_ORDENADA")',
    )
    normal, base = _sub("Import_CSV_Imos_1"), _sub("Import_Base_Imos_1")
    posicoes = [base.index(p) for p in passos]
    assert posicoes == sorted(posicoes)
    assert [normal.index(p) for p in passos] == sorted(normal.index(p) for p in passos)
    assert "Public Sub Import_Base_Imos_1(ByVal caminhoCSV As String)" in _codigo()
    assert "EncontrarCSVPorProcesso" not in base
    assert "Len(Dir(caminhoCSV)) = 0" in base


def test_uma_so_definicao_de_cada_macro() -> None:
    codigo = _codigo()
    for nome in ("Import_CSV_Imos_1", "Import_Base_Imos_1"):
        assert len(re.findall(rf"Sub {nome}\(", codigo)) == 1


def test_script_do_modelo_escreve_o_modulo() -> None:
    texto = SCRIPT.read_text(encoding="utf-8")
    assert '"modImportCSVImos_1",' in texto
    assert '"Sub Import_Base_Imos_1",' in texto
