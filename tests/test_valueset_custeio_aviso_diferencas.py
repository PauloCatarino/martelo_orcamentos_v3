"""O caminho ValueSet → Custeio: aviso ao mudar de separador e ver inativas."""

from __future__ import annotations

import inspect

import pytest

pytest.importorskip("PySide6")


def test_pagina_valueset_mostra_linhas_inativas_a_pedido() -> None:
    """Sem isto, desativar uma linha por engano não tinha volta."""
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    init = inspect.getsource(OrcamentoItemValuesetPage.__init__)
    assert "mostrar_inativas_check" in init
    assert "Mostrar inativas" in init

    carregar = inspect.getsource(OrcamentoItemValuesetPage.carregar)
    assert "mostrar_inativas_check.isChecked()" in carregar
    assert "listar_linhas_do_item" in carregar
    assert "listar_linhas_ativas_do_item" in carregar


def test_botao_atualizar_custeio_sem_selecao_pede_o_quadro_todo() -> None:
    from app.ui.pages.orcamento_item_valueset_page import OrcamentoItemValuesetPage

    assert hasattr(OrcamentoItemValuesetPage, "pedido_rever_diferencas")

    fonte = inspect.getsource(OrcamentoItemValuesetPage.atualizar_custeio_da_linha)
    assert "pedido_rever_diferencas.emit()" in fonte
    assert "_propagar_para_custeio" in fonte


def test_pagina_custeio_avisa_ao_voltar_do_valueset() -> None:
    from app.ui.pages.orcamento_item_custeio_page import OrcamentoItemCusteioPage

    for metodo in (
        "_on_separador_mudou",
        "rever_diferencas_valueset",
        "_perguntar_rever_diferencas",
    ):
        assert hasattr(OrcamentoItemCusteioPage, metodo)

    mudou = inspect.getsource(OrcamentoItemCusteioPage._on_separador_mudou)
    # Só pergunta a VOLTAR do ValueSet, não a ir para lá.
    assert "veio_do_valueset" in mudou
    assert "rever_diferencas_valueset" in mudou

    rever = inspect.getsource(OrcamentoItemCusteioPage.rever_diferencas_valueset)
    assert "listar_divergencias_valueset_do_item" in rever
    assert "DiferencasValuesetCusteioDialog" in rever
    assert "aplicar_divergencias_valueset" in rever
    assert "_recalcular_item_completo" in rever
    # Dizer "agora não" não pode pôr a pergunta a repetir-se a cada clique.
    assert "_divergencias_dispensadas" in rever


def test_dialogo_de_diferencas_marca_so_as_que_seguem_o_valueset() -> None:
    from app.ui.dialogs.diferencas_valueset_custeio_dialog import (
        DiferencasValuesetCusteioDialog,
    )

    assert DiferencasValuesetCusteioDialog.TABLE_HEADERS[0] == "Atualizar?"
    for coluna in (
        "Ref LE no custeio",
        "Ref LE no ValueSet",
        "Escolha manual",
        "O que muda",
    ):
        assert coluna in DiferencasValuesetCusteioDialog.TABLE_HEADERS

    preencher = inspect.getsource(DiferencasValuesetCusteioDialog._preencher)
    assert "divergencia.sugerido" in preencher

    aplicar = inspect.getsource(
        DiferencasValuesetCusteioDialog._atualizar_selecionadas
    )
    assert "divergencia.linha_id" in aplicar
    assert "divergencia.valueset_linha_id" in aplicar


def test_dialogo_de_diferencas_abre_largo() -> None:
    """São treze colunas: abrir estreito escondia logo as Ref LE."""
    from app.ui.dialogs.diferencas_valueset_custeio_dialog import (
        DiferencasValuesetCusteioDialog,
    )

    dimensionar = inspect.getsource(
        DiferencasValuesetCusteioDialog._dimensionar_ao_ecra
    )
    assert "availableGeometry" in dimensionar
    assert "0.96" in dimensionar

    init = inspect.getsource(DiferencasValuesetCusteioDialog.__init__)
    assert "_dimensionar_ao_ecra()" in init


def test_dropdowns_dentro_das_tabelas_ignoram_a_roda_do_rato() -> None:
    """A roda a passar por cima não pode trocar material nem tipo de produção."""
    from app.ui.pages import orcamento_item_custeio_page, orcamento_items_page

    for modulo in (orcamento_item_custeio_page, orcamento_items_page):
        fonte = inspect.getsource(modulo)
        assert "ComboSemScroll()" in fonte
        # Nenhum QComboBox cru ficou para trás nestas duas páginas.
        assert "QComboBox()" not in fonte


def test_nenhum_widget_sensivel_a_roda_ficou_cru_na_interface() -> None:
    """Mesma lógica em toda a app: combos, spins e datas passam pelos sem-roda."""
    import pathlib

    crus = []
    for caminho in sorted(pathlib.Path("app/ui").rglob("*.py")):
        if caminho.name == "combo_sem_scroll.py":
            continue
        fonte = caminho.read_text(encoding="utf-8")
        for widget in ("QComboBox()", "QSpinBox()", "QDoubleSpinBox()", "QDateEdit()"):
            if widget in fonte:
                crus.append(f"{caminho}: {widget}")

    assert crus == []
