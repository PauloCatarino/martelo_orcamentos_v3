"""O painel que abre, fecha e se põe em grande.

Nasceu da Pesquisa IA: quatro tabelas empilhadas, e as vazias a ocupar tanto
espaço como as cheias.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication, QLabel, QTableWidget

from app.ui.helpers.painel_recolhivel import (
    ALTURA_LIVRE,
    TEXTO_GRANDE,
    TEXTO_VOLTAR,
    PainelRecolhivel,
)

# Os widgets precisam de uma QApplication viva; e' o padrao dos outros
# testes de interface deste projeto.
_app = QApplication.instance() or QApplication([])


def _painel(titulo: str = "Artigos PHC") -> PainelRecolhivel:
    return PainelRecolhivel(titulo, QTableWidget(0, 3))


def test_nasce_aberto_mesmo_antes_de_aparecer_no_ecra() -> None:
    """O Qt diz que nada está visível até a página ser mostrada.

    Se o estado fosse lido do `isVisible()`, os painéis nasciam todos
    fechados sem ninguém os ter fechado.
    """
    painel = _painel()

    assert painel.esta_aberto()
    assert "▼" in painel.botao_titulo.text()


def test_clicar_no_titulo_fecha_e_volta_a_abrir() -> None:
    painel = _painel()

    painel.botao_titulo.click()
    assert not painel.esta_aberto()
    assert "▶" in painel.botao_titulo.text()
    # Fechado nao pode roubar espaco: fica so' com a altura do titulo.
    assert painel.maximumHeight() < ALTURA_LIVRE

    painel.botao_titulo.click()
    assert painel.esta_aberto()
    assert painel.maximumHeight() == ALTURA_LIVRE


def test_tabela_vazia_fecha_se_sozinha_e_diz_porque() -> None:
    painel = _painel()

    painel.definir_contagem(0, 4991, texto_vazio="Carregue o PHC primeiro.")

    assert not painel.esta_aberto()
    assert painel.label_vazio.text() == "Carregue o PHC primeiro."
    assert painel.label_conta.text() == "0 de 4991"


def test_ao_aparecerem_resultados_volta_a_abrir() -> None:
    painel = _painel()
    painel.definir_contagem(0, 4991, texto_vazio="Sem resultados.")

    painel.definir_contagem(17, 4991)

    assert painel.esta_aberto()
    assert painel.label_conta.text() == "17 de 4991"
    assert painel.label_vazio.text() == ""


def test_quem_fecha_a_mao_continua_fechado() -> None:
    """Fechar à mão é uma decisão da pessoa; não se desfaz sozinha."""
    painel = _painel()

    painel.botao_titulo.click()
    painel.definir_contagem(17, 4991)

    assert not painel.esta_aberto()


def test_contagem_com_detalhe() -> None:
    painel = _painel("Catálogos")

    painel.definir_contagem(30, detalhe="3 exactos")

    assert painel.label_conta.text() == "30 · 3 exactos"


def test_o_botao_grande_avisa_quem_monta_a_pagina() -> None:
    """O painel não conhece os irmãos: só pede, quem decide é a página."""
    painel = _painel()
    pedidos = []
    painel.grande_pedido.connect(pedidos.append)

    painel.botao_grande.click()

    assert pedidos == [painel]


def test_painel_sem_botao_grande() -> None:
    """A resposta IA não precisa de ecrã inteiro: é texto, não uma tabela."""
    painel = PainelRecolhivel("Resposta", QLabel("texto"), com_botao_grande=False)

    assert painel.botao_grande is None


def test_botao_grande_diz_o_que_faz_em_palavras() -> None:
    """Setas como ⤢ nem sempre existem nas fontes do Windows: sairiam quadrados."""
    painel = _painel()

    assert painel.botao_grande.text() == TEXTO_GRANDE
    painel.definir_em_grande(True)
    assert painel.botao_grande.text() == TEXTO_VOLTAR
