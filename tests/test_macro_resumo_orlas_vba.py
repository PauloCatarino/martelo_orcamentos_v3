"""Guarda a macro que gera a folha ResumoOrlas (fonte em scripts/vba).

O código corre dentro do modelo Excel `Lista_Material_IMOS_MARTELO.xltm`; a
fonte de verdade é o .bas do repositório, que o script
`atualizar_macros_modelo_lista_material.py` escreve no modelo.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MODULO = RAIZ / "scripts" / "vba" / "modResumoOrlas.bas"


def _codigo() -> str:
    return MODULO.read_text(encoding="cp1252")


def test_ref_cliente_fica_em_f1_f2() -> None:
    codigo = _codigo()

    assert 'wsDst.Range("F1").Value = "REF_CLIENTE"' in codigo
    assert 'wsDst.Range("F2").Value = refCli' in codigo
    # O sítio antigo (H1/H2) só se limpa, nunca se escreve.
    assert 'wsDst.Range("H1").Value =' not in codigo
    assert 'wsDst.Range("H2").Value =' not in codigo
    assert 'wsDst.Range("H1:H2").ClearContents' in codigo


def test_titulos_da_tabela_iguais_aos_do_modelo() -> None:
    codigo = _codigo()

    assert 'Private Const VALOR_STOCK_ENC As String = "stock/enc"' in codigo
    assert (
        '"Material", "Nome_Orlas", "ML_QT", _\n'
        '        VALOR_STOCK_ENC, "Marca / Ref.", "Larg X Esp", "ML", "Obs." _'
    ) in codigo
    assert '"LARG X ESP", "ML", "Entrada Orlas"' not in codigo


def test_cada_linha_leva_stock_enc_e_o_antigo_enc_passa_a_stock_enc() -> None:
    codigo = _codigo()

    assert "outArr(i, 4) = VALOR_STOCK_ENC" in codigo
    assert 'outArr(i, 4) = "enc"' not in codigo
    assert 'LCase$(Trim$(CStr(man(0)))) <> "enc"' in codigo


def test_obras_antigas_mantem_o_que_foi_escrito_a_mao() -> None:
    codigo = _codigo()

    # Novos nomes primeiro, os antigos como recurso.
    assert 'cEnc = GetListColIndexByNorm(lo, "STOCKENC")' in codigo
    assert 'If cEnc = 0 Then cEnc = GetListColIndexByNorm(lo, "ENC")' in codigo
    assert 'cEntrada = GetListColIndexByNorm(lo, "OBS")' in codigo
    assert (
        'If cEntrada = 0 Then cEntrada = GetListColIndexByNorm(lo, "ENTRADAORLAS")'
        in codigo
    )


def test_script_do_modelo_escreve_este_modulo() -> None:
    spec = importlib.util.spec_from_file_location(
        "atualizar_macros", RAIZ / "scripts" / "atualizar_macros_modelo_lista_material.py"
    )
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)

    assert "modResumoOrlas" in modulo.MODULOS
    assert "VALOR_STOCK_ENC" in modulo._marcadores(MODULO)
