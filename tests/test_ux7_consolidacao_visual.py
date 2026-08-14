from __future__ import annotations

import inspect
import re
from pathlib import Path

from PySide6.QtWidgets import QApplication, QHeaderView, QTableWidget

from app.ui.widgets.larguras_colunas import ligar_persistencia_larguras


def test_helper_converte_todos_modos_em_interativos() -> None:
    app = QApplication.instance() or QApplication([])
    tabela = QTableWidget(0, 3)
    tabela.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    tabela.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
    ligar_persistencia_larguras(tabela, "teste_ux7_interativas")
    assert all(
        tabela.horizontalHeader().sectionResizeMode(col) == QHeaderView.ResizeMode.Interactive
        for col in range(3)
    )
    assert not tabela.horizontalHeader().stretchLastSection()
    tabela.deleteLater(); app.processEvents()


def test_dialogos_operacionais_guardam_larguras() -> None:
    from app.ui.dialogs.atualizar_precos_valueset_dialog import AtualizarPrecosValuesetDialog
    from app.ui.dialogs.converter_orcamento_dialog import ConverterOrcamentoDialog
    from app.ui.dialogs.escaloes_area_dialog import EscaloesAreaDialog
    from app.ui.dialogs.importar_valueset_modelo_dialog import ImportarValuesetModeloDialog
    from app.ui.dialogs.modulo_linhas_dialog import ModuloLinhasDialog
    from app.ui.dialogs.propagar_valueset_custeio_dialog import PropagarValuesetCusteioDialog
    from app.ui.dialogs.ref_cliente_duplicada_dialog import RefClienteDuplicadaDialog
    from app.ui.dialogs.valueset_linha_operacoes_dialog import ValuesetLinhaOperacoesDialog
    classes = (AtualizarPrecosValuesetDialog, ConverterOrcamentoDialog, EscaloesAreaDialog,
               ImportarValuesetModeloDialog, ModuloLinhasDialog, PropagarValuesetCusteioDialog,
               RefClienteDuplicadaDialog, ValuesetLinhaOperacoesDialog)
    for classe in classes:
        assert "ligar_persistencia_larguras" in inspect.getsource(classe)


def test_tema_global_inclui_controlos_e_abas() -> None:
    from app.ui import tema
    assert "QPushButton" in tema.ESTILO_GLOBAL
    assert "QLineEdit" in tema.ESTILO_GLOBAL
    assert "QGroupBox" in tema.ESTILO_GLOBAL
    assert "QTabBar" in tema.ESTILO_GLOBAL


def test_tema_global_uniformiza_hover_e_selecao_das_vistas_de_dados() -> None:
    from app.ui import tema

    estilo = tema.ESTILO_REALCE_VISTAS_DADOS
    for vista in ("QTableView", "QTableWidget", "QTreeView", "QTreeWidget"):
        assert f"{vista}::item:hover" in estilo
        assert f"{vista}::item:selected" in estilo

    assert f"background-color: {tema.CASTANHO_ESCURO}" in estilo
    assert "color: #FFFFFF" in estilo
    assert estilo in tema.ESTILO_GLOBAL


def test_cabecalho_comum_fica_castanho_com_texto_branco() -> None:
    from app.ui import tema

    estilo = tema.ESTILO_CABECALHO_VISTAS_DADOS
    assert f"background-color: {tema.CASTANHO_MEDIO}" in estilo
    assert "color: #FFFFFF" in estilo
    assert estilo in tema.ESTILO_GLOBAL


def test_checks_de_vistas_de_dados_usam_indicador_visivel() -> None:
    from app.ui import tema

    estilo = tema.ESTILO_CHECKS_VISTAS_DADOS
    for vista in (
        "QTableView",
        "QTableWidget",
        "QListView",
        "QListWidget",
        "QTreeView",
        "QTreeWidget",
    ):
        assert f"{vista}::indicator:checked" in estilo

    assert "check_indicator_checked.svg" in estilo
    assert estilo in tema.ESTILO_GLOBAL


def test_paginas_nao_reintroduzem_estilos_locais_conflitantes() -> None:
    raiz_ui = Path(__file__).parents[1] / "app" / "ui"
    padrao_realce = re.compile(
        r"Q(?:Table|Tree)(?:View|Widget)::item:(?:hover|selected)"
    )
    padrao_cabecalho = re.compile(r"QHeaderView::section(?!:)\s*\{")
    conflitos: list[str] = []

    for caminho in raiz_ui.rglob("*.py"):
        if caminho.name == "tema.py":
            continue
        fonte = caminho.read_text(encoding="utf-8")
        if padrao_realce.search(fonte) or padrao_cabecalho.search(fonte):
            conflitos.append(str(caminho.relative_to(raiz_ui)))

    assert conflitos == []
