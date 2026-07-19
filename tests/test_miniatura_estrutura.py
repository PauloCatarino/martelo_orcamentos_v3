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
    criar_miniatura_estrutura,
    criar_miniatura_estrutura_componentes,
    PUXADOR,
    resolver_funcao_estrutural,
    tem_previsao_estrutural,
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
