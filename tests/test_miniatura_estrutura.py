"""Coverage for the illustrative structural cube used in costing."""

from __future__ import annotations

import os
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.domain.peca_funcao_types import (
    COSTA,
    LATERAL,
    PORTA,
    PRATELEIRA_AMOVIVEL,
    TETO,
)
from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage
from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)
from app.ui.widgets.miniatura_estrutura import (
    _posicoes_puxadores_porta,
    criar_miniatura_estrutura,
    criar_miniatura_estrutura_componentes,
    PUXADOR,
    resolver_funcao_estrutural,
    tem_previsao_estrutural,
)
from app.ui.widgets.miniatura_ferragem import (
    CORREDICA,
    DOBRADICA,
    PE,
    PUXADOR as PUXADOR_FERRAGEM,
    criar_miniatura_ferragem,
    resolver_ferragem_visual,
)

_app = QApplication.instance() or QApplication([])


def test_reconhece_as_funcoes_estruturais_representaveis() -> None:
    assert tem_previsao_estrutural(TETO) is True
    assert tem_previsao_estrutural(COSTA) is True
    assert tem_previsao_estrutural("FERRAGEM") is False
    assert resolver_funcao_estrutural(None, "PRATELEIRA_AMOVIVEL") == PRATELEIRA_AMOVIVEL


def test_miniatura_tem_tamanho_fixo_e_muda_com_a_estrutura() -> None:
    teto = criar_miniatura_estrutura(TETO, 1)
    porta_dupla = criar_miniatura_estrutura(PORTA, 2)
    lateral_dupla = criar_miniatura_estrutura(LATERAL, 2)

    assert teto.size().width() == 28
    assert teto.size().height() == 28
    assert teto.toImage() != porta_dupla.toImage()
    assert porta_dupla.toImage() != lateral_dupla.toImage()


def test_coluna_modulo_prioriza_a_miniatura_estrutural_da_peca() -> None:
    page = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    page._estruturas_visuais_por_linha = {1: [(TETO, 1)]}
    linha = SimpleNamespace(id=1, quantidade=1, modulo_imagem_path=None)

    item = page._criar_item_modulo(linha)

    assert item.icon().isNull() is False
    assert "Representação estrutural ilustrativa" in item.toolTip()


def test_a_ferragem_nao_leva_cubo_mesmo_com_nome_de_peca() -> None:
    # RODAS_PORTA_CORRER_SUP lia-se como "porta" e ganhava o cubo da porta.
    page = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    page._estruturas_visuais_por_linha = {1: [(PORTA, 1)]}
    linha = SimpleNamespace(
        id=1,
        tipo_linha="FERRAGEM",
        quantidade=1,
        modulo_imagem_path=None,
    )

    item = page._criar_item_modulo(linha)

    assert page._partes_estruturais_a_desenhar(linha) == []
    assert item.icon().isNull() is True
    assert item.toolTip() == ""


def test_reconhece_apenas_as_quatro_ferragens_com_icon_proprio() -> None:
    assert resolver_ferragem_visual("FERRAGEM_DOBRADICA") == DOBRADICA
    assert resolver_ferragem_visual("FERRAGEM_PE_NIVELADOR") == PE
    assert resolver_ferragem_visual("CORREDICA") == CORREDICA
    assert resolver_ferragem_visual("PUXADOR_PORTA_CORRER") == PUXADOR_FERRAGEM
    # Estas ferragens não são um pé nem um puxador, apesar das palavras parciais.
    assert resolver_ferragem_visual("NIVELADORES/PENDURAIS") is None
    assert resolver_ferragem_visual("FERRAGEM_ESQUADRO_L_PUX_GOLA") is None
    assert resolver_ferragem_visual("RODAS_PORTA_CORRER") is None


def test_icons_de_ferragem_sao_distintos_e_tem_o_tamanho_da_coluna() -> None:
    imagens = [
        criar_miniatura_ferragem(tipo)
        for tipo in (PUXADOR_FERRAGEM, DOBRADICA, CORREDICA, PE)
    ]

    assert all(imagem.width() == 28 and imagem.height() == 28 for imagem in imagens)
    assert all(not imagem.isNull() for imagem in imagens)
    assert len({bytes(imagem.toImage().constBits()) for imagem in imagens}) == 4


def test_coluna_modulo_mostra_icon_e_tooltip_nas_ferragens_suportadas() -> None:
    page = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    casos = (
        ("FERRAGEM_DOBRADICA", "Dobradiça"),
        ("FERRAGEM_PE_NIVELADOR", "Pé nivelador"),
        ("FERRAGEM_CORREDICA", "Corrediça"),
        ("FERRAGEM_PUXADOR", "Puxador"),
    )

    for indice, (chave, nome) in enumerate(casos, start=1):
        linha = SimpleNamespace(
            id=indice,
            tipo_linha="FERRAGEM",
            chave_valueset=chave,
            def_peca_codigo=None,
            codigo=None,
            descricao_no_orcamento=None,
            descricao="Ferragem",
            modulo_imagem_path=None,
        )
        item = page._criar_item_modulo(linha)

        assert item.icon().isNull() is False
        assert f"ferragem: {nome}" in item.toolTip()
        assert "não altera quantidades" in item.toolTip()


def test_ferragem_desconhecida_continua_sem_icon() -> None:
    page = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    linha = SimpleNamespace(
        id=1,
        tipo_linha="FERRAGEM",
        chave_valueset="FERRAGEM_UNIOES",
        def_peca_codigo="SISTEMAS_UNIAO",
        codigo="SISTEMAS_UNIAO",
        descricao_no_orcamento="Cavilhas e parafusos",
        descricao="Uniões",
        modulo_imagem_path=None,
    )

    item = page._criar_item_modulo(linha)

    assert item.icon().isNull() is True
    assert item.toolTip() == ""


def test_a_peca_continua_a_levar_o_cubo() -> None:
    page = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    page._estruturas_visuais_por_linha = {1: [(LATERAL, 1)]}
    linha = SimpleNamespace(
        id=1, tipo_linha="PECA", quantidade=1, modulo_imagem_path=None
    )

    assert page._partes_estruturais_a_desenhar(linha) == [(LATERAL, 1)]
    assert page._criar_item_modulo(linha).icon().isNull() is False


def test_a_ferragem_ainda_conta_para_o_desenho_da_composta() -> None:
    # Na linha da ferragem nao se desenha nada, mas ela continua a somar ao
    # cubo da peça composta onde entra (por exemplo o puxador da porta).
    page = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    page._funcoes_estruturais_por_peca = {10: PORTA}
    composta = SimpleNamespace(
        id=1,
        linha_pai_id=None,
        tipo_linha="PECA_COMPOSTA",
        def_peca_id=None,
        def_peca_codigo="PORTA+PUXADOR",
        codigo=None,
        quantidade=1,
        modulo_imagem_path=None,
    )
    porta = SimpleNamespace(
        id=2,
        linha_pai_id=1,
        tipo_linha="PECA",
        def_peca_id=10,
        def_peca_codigo="PORTA_SIMPLES",
        codigo=None,
        quantidade=1,
    )
    puxador = SimpleNamespace(
        id=3,
        linha_pai_id=1,
        tipo_linha="FERRAGEM",
        def_peca_id=None,
        def_peca_codigo="PUXADOR_TIC_TAC",
        codigo=None,
        quantidade=1,
    )

    page._estruturas_visuais_por_linha = page._mapear_estruturas_visuais(
        [composta, porta, puxador]
    )

    assert page._estruturas_visuais_por_linha[1] == [(PORTA, 1), (PUXADOR, 1)]
    assert page._partes_estruturais_a_desenhar(composta) == [(PORTA, 1), (PUXADOR, 1)]
    assert page._partes_estruturais_a_desenhar(puxador) == []


def test_composta_mostra_a_porta_dupla_dos_componentes() -> None:
    page = OrcamentoItemCusteioPage.__new__(OrcamentoItemCusteioPage)
    page._funcoes_estruturais_por_peca = {10: PORTA}
    composta = SimpleNamespace(
        id=1,
        linha_pai_id=None,
        tipo_linha="PECA_COMPOSTA",
        def_peca_id=None,
        def_peca_codigo="PORTA_DUPLA",
        codigo=None,
        quantidade=1,
    )
    porta = SimpleNamespace(
        id=2,
        linha_pai_id=1,
        tipo_linha="PECA",
        def_peca_id=10,
        def_peca_codigo="PORTA_SIMPLES",
        codigo=None,
        quantidade=2,
    )

    estruturas = page._mapear_estruturas_visuais([composta, porta])

    assert estruturas[1] == [(PORTA, 2)]


def test_porta_com_puxador_e_gaveta_tem_previsoes_distintas() -> None:
    porta = criar_miniatura_estrutura_componentes([(PORTA, 2)])
    porta_com_puxador = criar_miniatura_estrutura_componentes(
        [(PORTA, 2), (PUXADOR, 1)]
    )
    gaveta = criar_miniatura_estrutura_componentes(
        [
            (resolver_funcao_estrutural(None, "FRENTE_GAVETA"), 1),
            (resolver_funcao_estrutural(None, "LADO_GAVETA"), 2),
            (resolver_funcao_estrutural(None, "TRASEIRA_GAVETA"), 1),
            (resolver_funcao_estrutural(None, "FUNDO_GAVETA"), 1),
            (PUXADOR, 1),
        ]
    )

    assert porta.toImage() != porta_com_puxador.toImage()
    assert gaveta.toImage() != porta.toImage()


def test_porta_dupla_coloca_um_puxador_de_cada_lado_da_divisao() -> None:
    esquerda, direita = _posicoes_puxadores_porta(2)

    assert esquerda < 14.2 < direita
    assert direita - esquerda > 4
    assert _posicoes_puxadores_porta(1) == (19.0,)


def test_largura_inicial_da_porta_respeita_a_quantidade() -> None:
    porta = SimpleNamespace(funcao=PORTA, codigo="PORTA_SIMPLES")
    simples: dict = {}
    dupla: dict = {}

    OrcamentoItemCusteioLinhaService._aplicar_largura_padrao_porta(
        simples, porta, 1
    )
    OrcamentoItemCusteioLinhaService._aplicar_largura_padrao_porta(dupla, porta, 2)

    assert simples["larg"] == "LM"
    assert dupla["larg"] == "LM/2"
