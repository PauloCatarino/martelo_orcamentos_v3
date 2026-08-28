"""Guarda a macro de importação das listas IMOS (fonte em scripts/vba).

O código corre dentro do modelo Excel, mas a fonte de verdade é o .bas do
repositório: é ele que o script `atualizar_macros_modelo_lista_material.py`
escreve no `Lista_Material_IMOS_MARTELO.xltm`.
"""

from __future__ import annotations

from pathlib import Path

MODULO = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "vba"
    / "Import_List_Ferr_Etiq_11.bas"
)


def _codigo() -> str:
    return MODULO.read_text(encoding="cp1252")


def test_separadores_imos_sao_procurados_pelo_nome() -> None:
    codigo = _codigo()

    assert "Private Function IMOS_IndiceFolhaPorNome" in codigo
    assert 'IMOS_IndiceFolhaPorNome(wbImportar, "FERRAGENS")' in codigo
    assert 'IMOS_IndiceFolhaPorNome(wbImportar, "PURCH")' in codigo
    assert 'IMOS_IndiceFolhaPorNome(wbImportar, "SPP")' in codigo


def test_so_importa_os_separadores_que_existem() -> None:
    codigo = _codigo()

    for indice, destino in (
        ("idxFerr", "1_FERRAGENS"),
        ("idxPurch", "2_PURCH"),
        ("idxSpp", "3_SPP"),
    ):
        assert f"If {indice} > 0 Then" in codigo
        assert (
            f'IMOS_CopiarFolhaComNome(wbImportar, {indice}, wbAtual, shAfter, "{destino}")'
            in codigo
        )

    # A ordem das folhas deixou de mandar nas listas de ferragens; sobra apenas
    # como recurso para ficheiros antigos, dentro do bloco de fallback.
    # (A etiqueta vem de outro ficheiro, com uma folha só, e essa continua a 1.)
    copias_por_posicao = [
        linha
        for linha in codigo.splitlines()
        if "IMOS_CopiarFolhaComNome(wbImportar, " in linha
        and "ETIQUETA" not in linha
        and "idx" not in linha
    ]
    assert copias_por_posicao == []


def test_ficheiros_antigos_sem_nomes_usam_a_ordem_das_folhas() -> None:
    codigo = _codigo()

    assert "If idxFerr = 0 And idxPurch = 0 And idxSpp = 0 Then" in codigo
    assert "If wbImportar.Worksheets.Count >= 1 Then idxFerr = 1" in codigo
    assert "If wbImportar.Worksheets.Count >= 3 Then idxSpp = 3" in codigo


def test_nome_do_separador_ignora_numero_e_espacos() -> None:
    codigo = _codigo()

    assert "Private Function IMOS_NomeBaseFolha" in codigo
    assert 's = Replace(s, " ", "")' in codigo
