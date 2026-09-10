"""O que a vista geral da Pesquisa IA escreve em cada celula.

Sao funcoes puras de proposito: a pagina que as usa e' Qt e so' se testa com
uma aplicacao de pe', e o que aqui se guarda -- qual o preco que se mostra
quando ha' onze -- nao tem nada a ver com widgets.
"""

from __future__ import annotations

from app.domain.pesquisa_ia_consulta import (
    grupo_ou_tipo,
    referencia_com_acabamento,
    valor_de_referencia,
)

# ---------------------------------------------------------------------------
# O que se mostra na vista geral
# ---------------------------------------------------------------------------


def test_o_valor_segue_a_espessura_pedida():
    precos = {"8mm": "6,19 €", "19mm": "8,74 €", "38mm": "17,21 €"}
    assert valor_de_referencia(precos, 19) == "8,74 €"


def test_sem_espessura_pedida_mostra_o_intervalo():
    """Do mais fino ao mais grosso — sem escolher uma espessura por ninguém."""
    precos = {"8mm": "6,19 €", "19mm": "8,74 €", "38mm": "17,21 €"}
    assert valor_de_referencia(precos) == "6,19 € a 17,21 €"


def test_uma_ferragem_tem_um_preco_e_e_esse_que_se_mostra():
    assert valor_de_referencia({"Preço un.": "9,02 €"}) == "9,02 €"


def test_uma_espessura_que_a_referencia_nao_tem_cai_no_intervalo():
    precos = {"8mm": "6,19 €", "19mm": "8,74 €"}
    assert valor_de_referencia(precos, 25) == "6,19 € a 8,74 €"


def test_sem_precos_diz_que_nao_ha():
    """Vazio parecia erro de leitura; «sem preço» é uma resposta."""
    assert valor_de_referencia({}) == "sem preço"
    assert valor_de_referencia({}, 19) == "sem preço"


def test_a_barra_do_acabamento_so_aparece_quando_ha_acabamento():
    assert referencia_com_acabamento("W908", "SM") == "W908/SM"
    assert referencia_com_acabamento("22.8000", "") == "22.8000"


def test_uma_placa_diz_o_grupo_de_preco():
    assert grupo_ou_tipo("Grupo 0", "Eurodekor Tableros de partículas") == "Grupo 0"


def test_uma_ferragem_sem_grupo_diz_a_familia_do_catalogo():
    """O Casa Trend não preenche o grupo, e a célula ficava vazia à toa."""
    assert grupo_ou_tipo("", "Casa Banho Tulhas Roupa") == "Casa Banho Tulhas Roupa"


def test_sem_grupo_nem_tipo_fica_vazio():
    """A Emuca não tem coluna nenhuma disso — vazio é a verdade."""
    assert grupo_ou_tipo("", "") == ""
    assert grupo_ou_tipo(None, None) == ""


def test_um_grupo_so_de_espacos_nao_conta_como_grupo():
    assert grupo_ou_tipo("   ", "Casa Banho Tulhas Roupa") == "Casa Banho Tulhas Roupa"
