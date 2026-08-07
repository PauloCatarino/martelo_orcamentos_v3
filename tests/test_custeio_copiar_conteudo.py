from app.services.orcamento_item_custeio_linha_service import (
    OrcamentoItemCusteioLinhaService,
)


def test_servico_custeio_nao_expoe_copia_de_conteudo() -> None:
    assert not hasattr(OrcamentoItemCusteioLinhaService, "copiar_conteudo_linha")


def test_servico_custeio_nao_expoe_colagem_de_conteudo() -> None:
    assert not hasattr(OrcamentoItemCusteioLinhaService, "colar_conteudo_linha")


def test_pagina_custeio_nao_expoe_acoes_de_conteudo() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    assert not hasattr(OrcamentoItemCusteioPage, "copiar_dados")
    assert not hasattr(OrcamentoItemCusteioPage, "colar_dados")
