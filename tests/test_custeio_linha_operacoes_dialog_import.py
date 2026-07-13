"""Checks for the costing-line effective-operations detail."""

from __future__ import annotations

import inspect


def test_dialogo_operacoes_custeio_importa_e_tem_edicao_local() -> None:
    from app.ui.dialogs.custeio_linha_operacoes_dialog import (
        CusteioLinhaOperacoesDialog,
    )

    source = inspect.getsource(CusteioLinhaOperacoesDialog)
    assert "Edição local ativa" in source
    assert "Custo produção total" in source
    assert "NoEditTriggers" in source
    assert "Nova operação" in source
    assert "Editar operação" in source
    assert "Remover operação" in source
    assert "Repor operações da origem" in source
    assert "Ferragem sem operações efetivas" in source


def test_pagina_custeio_edita_operacoes_sem_criar_linhas_principais() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    source = inspect.getsource(OrcamentoItemCusteioPage.abrir_operacoes_da_linha)
    assert "listar_operacoes_efetivas_da_linha" in source
    assert "CusteioLinhaOperacoesDialog" in source
    assert "adicionar_operacao_local" in source
    assert "editar_operacao_efetiva_local" in source
    assert "remover_operacao_local" in source
    assert "repor_operacoes_da_origem" in source
    assert "create_linha" not in source
    assert "update_linha" not in source
