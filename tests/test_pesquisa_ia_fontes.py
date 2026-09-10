"""De onde vieram os valores que a resposta IA apresenta.

O Paulo pediu para ver a origem à frente da resposta. A lista NÃO é pedida ao
modelo: um modelo pequeno inventa a fonte com a mesma facilidade com que
inventa o preço. É montada com o que realmente lhe foi entregue.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.domain.pesquisa_ia_resumo import comparar_fornecedores
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
    assert "• Referências de catálogos: H3170 (Ref_EGGER)" in texto
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
        "• Referências de catálogos: H3170 "
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


# ---------------------------------------------------------------------------
# A quem se compra mais barato
# ---------------------------------------------------------------------------


def _ref(referencia, fornecedor, folha, precos):
    return SimpleNamespace(referencia=referencia, fornecedor=fornecedor, folha=folha,
                           st_acab="", nome_design="", grupo="", tipo="", precos=precos)


def test_a_mesma_referencia_em_dois_fornecedores_da_o_mais_barato_primeiro():
    """A pergunta que motivou o projeto todo, respondida por conta.

    Um modelo pequeno perguntado por «quanto custa o W908 em 19mm» responde
    com o primeiro preço que lhe aparece à frente — e respondeu 9,32 €, sem
    dizer que a WoodSide tem o mesmo a 8,74 €.
    """
    linhas = [
        _ref("W908", "Balbino & Faustino", "Stock_B&F_Egger", {"8mm": "6,73 €", "19mm": "9,32 €"}),
        _ref("W908", "WoodSide", "Stock_WoodSide_Egger", {"8mm": "6,19 €", "19mm": "8,74 €"}),
    ]

    frases = comparar_fornecedores(linhas)

    assert len(frases) == 2
    de_19 = next(f for f in frases if "19mm" in f)
    assert de_19.index("8,74") < de_19.index("9,32"), "o mais barato vem primeiro"
    assert "WoodSide" in de_19 and "Balbino & Faustino" in de_19
    assert "diferença de 0,58" in de_19


def test_o_mesmo_preco_em_dois_fornecedores_nao_e_comparacao():
    """Sem diferença não há nada a decidir — e a lista tem de ficar curta."""
    linhas = [
        _ref("W908", "A", "F1", {"19mm": "9,32 €"}),
        _ref("W908", "B", "F2", {"19mm": "9,32 €"}),
    ]
    assert comparar_fornecedores(linhas) == []


def test_uma_referencia_num_fornecedor_so_nao_gera_comparacao():
    assert comparar_fornecedores([_ref("W908", "A", "F1", {"19mm": "9,32 €"})]) == []


def test_um_preco_ilegivel_nao_rebenta_a_comparacao():
    linhas = [
        _ref("X", "A", "F1", {"19mm": "sob consulta"}),
        _ref("X", "B", "F2", {"19mm": "9,32 €"}),
    ]
    assert comparar_fornecedores(linhas) == []
