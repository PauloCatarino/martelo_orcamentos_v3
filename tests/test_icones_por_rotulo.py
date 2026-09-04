"""Os ícones dos botões saem do texto de cada um.

O programa tem quase 400 botões e os nomes repetem-se de página para página.
Pôr o ícone à mão em cada um dava resultados diferentes conforme quem o fizesse
— e os botões novos nasciam sem nada. Assim é o texto que decide.
"""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QHBoxLayout, QPushButton  # noqa: E402

from app.ui.icones import (  # noqa: E402
    decorar_barra,
    decorar_botoes,
    icone,
    nome_icone_para_rotulo,
)


@pytest.fixture(scope="module")
def app():
    yield QApplication.instance() or QApplication([])


@pytest.mark.parametrize(
    ("rotulo", "esperado"),
    [
        ("Novo Orçamento", "orcamento_novo"),
        ("Nova Peça", "orcamento_novo"),
        ("Novo", "orcamento_novo"),
        ("+ Nova matéria-prima", "orcamento_novo"),
        ("Editar Item", "orcamento_editar"),
        # "Abrir / Editar" é editar, não abrir: a ordem das regras conta.
        ("Abrir / Editar Peça", "orcamento_editar"),
        ("Abrir Modelo", "orcamento_abrir"),
        ("Eliminar Orçamento", "orcamento_eliminar"),
        ("Remover Item", "orcamento_eliminar"),
        ("Atualizar", "atualizar"),
        ("Sincronizar PHC", "atualizar"),
        ("Ativar/Desativar", "acao_ativar_desativar"),
        ("Guardar Configurações", "acao_guardar"),
        ("Voltar aos Items", "acao_voltar"),
        ("Importar Modelo", "acao_importar"),
        ("Exportar PDF", "acao_exportar"),
        ("Limpar Dados", "acao_limpar"),
        ("Inserir Divisão", "acao_adicionar"),
        ("Pasta do Orçamento", "pasta_abrir"),
        # Sem correspondência: fica sem ícone, e ainda bem.
        ("Cancelar", None),
        ("Fechar", None),
        ("Definições de Peças", None),
        ("", None),
    ],
)
def test_o_texto_escolhe_o_icone(rotulo: str, esperado: str | None) -> None:
    assert nome_icone_para_rotulo(rotulo) == esperado


def test_todos_os_icones_do_mapa_existem_mesmo(app) -> None:
    """Um SVG em falta não dá erro: o botão fica só sem ícone."""
    from app.ui.icones import _ICONE_POR_PREFIXO

    for _prefixos, nome in _ICONE_POR_PREFIXO:
        assert not icone(nome).isNull(), f"{nome}.svg não carregou"


def test_nao_pisa_um_icone_escolhido_a_mao(app) -> None:
    botao = QPushButton("Atualizar")
    proprio = icone("pasta_abrir")
    botao.setIcon(proprio)

    assert decorar_botoes(botao) == 0
    assert botao.icon().cacheKey() == proprio.cacheKey()


def test_decora_a_barra_toda_de_uma_vez(app) -> None:
    barra = QHBoxLayout()
    botoes = [QPushButton(t) for t in ("Novo Item", "Editar Item", "Cancelar")]
    for botao in botoes:
        barra.addWidget(botao)

    assert decorar_barra(barra) == 2
    assert not botoes[0].icon().isNull()
    assert not botoes[1].icon().isNull()
    assert botoes[2].icon().isNull()


def test_a_janela_principal_decora_cada_pagina_que_regista() -> None:
    from app.ui.main_window import MainWindow

    fonte = inspect.getsource(MainWindow._add_page)
    assert "decorar_botoes(*page.findChildren(QPushButton))" in fonte
