"""Contracts for the item operation-audit dialog."""

from __future__ import annotations

import inspect


def test_dialogo_auditoria_operacoes_expoe_diagnostico_e_navegacao() -> None:
    from app.ui.dialogs.custeio_operacoes_auditoria_dialog import (
        CusteioOperacoesAuditoriaDialog,
    )

    assert "Estado" in CusteioOperacoesAuditoriaDialog.HEADERS
    assert "Operações" in CusteioOperacoesAuditoriaDialog.HEADERS
    assert "Custo produção" in CusteioOperacoesAuditoriaDialog.HEADERS
    source = inspect.getsource(CusteioOperacoesAuditoriaDialog)
    assert "Sem operações" in source
    assert "Abrir operações da linha" in source
    assert "NoEditTriggers" in source


def test_pagina_custeio_liga_auditoria_ao_detalhe_da_linha() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    init = inspect.getsource(OrcamentoItemCusteioPage.__init__)
    abrir = inspect.getsource(OrcamentoItemCusteioPage.auditar_operacoes_do_item)
    assert "Auditar operações" in init
    assert "auditar_operacoes_do_item" in abrir
    assert "selecionar_linha_por_id" in abrir
    assert "abrir_operacoes_da_linha" in abrir
