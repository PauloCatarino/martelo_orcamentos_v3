"""De onde vieram os valores que a resposta IA apresenta.

O Paulo pediu para ver a origem à frente da resposta. A lista NÃO é pedida ao
modelo: um modelo pequeno inventa a fonte com a mesma facilidade com que
inventa o preço. É montada com o que realmente lhe foi entregue.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.ui.pages.pesquisa_ia_page import montar_fontes


def _materia(ref_le: str):
    return SimpleNamespace(ref_le=ref_le)


def _referencia(nome: str, folha: str):
    return SimpleNamespace(referencia=nome, folha=folha)


def _trecho(ficheiro: str, local: str):
    return SimpleNamespace(ficheiro=ficheiro, local=local)


def test_sem_dados_nao_escreve_nada() -> None:
    assert montar_fontes([], [], [], []) == ""


def test_lista_as_origens_de_cada_tabela() -> None:
    texto = montar_fontes(
        [_materia("PLC0019"), _materia("PLC0021")],
        [{"Ref": "FO01283"}],
        [_referencia("H3170", "Ref_EGGER")],
        [_trecho("12_Placas.xlsx", "Folha Stock_Somapil / linha 7")],
    )

    assert texto.startswith("\n\nFontes:\n")
    assert "• Matérias-primas V3: PLC0019 | PLC0021" in texto
    assert "• PHC: FO01283" in texto
    assert "• Referências de placas: H3170 (Ref_EGGER)" in texto
    assert "• 12_Placas.xlsx (Folha Stock_Somapil / linha 7)" in texto


def test_a_mesma_referencia_em_varias_folhas_mostra_todas() -> None:
    """O H3170 tem preços diferentes conforme a folha — é isso que interessa."""
    texto = montar_fontes(
        [],
        [],
        [
            _referencia("H3170", "Ref_EGGER"),
            _referencia("H3170", "Stock_B&F_Egger"),
            _referencia("H3170", "Stock_WoodSide_Egger"),
        ],
        [],
    )

    assert (
        "• Referências de placas: H3170 "
        "(Ref_EGGER | Stock_B&F_Egger | Stock_WoodSide_Egger)" in texto
    )


def test_trechos_do_mesmo_ficheiro_ficam_numa_linha_so() -> None:
    texto = montar_fontes(
        [],
        [],
        [],
        [
            _trecho("12_Placas.xlsx", "Folha A / linha 7"),
            _trecho("12_Placas.xlsx", "Folha B / linha 9"),
            _trecho("Tabela Blum.pdf", "Página 4"),
        ],
    )

    assert "• 12_Placas.xlsx (Folha A / linha 7 | Folha B / linha 9)" in texto
    assert "• Tabela Blum.pdf (Página 4)" in texto


def test_referencias_vazias_nao_entram() -> None:
    """Uma linha do PHC sem Ref não pode virar uma fonte em branco."""
    texto = montar_fontes([_materia("")], [{"Ref": None}], [], [])

    assert texto == ""
