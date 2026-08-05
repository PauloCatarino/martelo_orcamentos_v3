"""O diálogo de importar modelo mostra o mesmo que a página dos modelos."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="module")
def _app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


def _modelo(**campos) -> SimpleNamespace:
    base = {
        "id": 1,
        "codigo": "ROUP_STD",
        "nome": "Roupeiros Interiores | Frentes | Ferragens",
        "descricao": "Interiores MLM LINHO + Frentes MDF MR BRANCO B3002",
        "observacoes": "Ferragens Standard",
        "tipo": "ROUPEIRO",
        "ambito": "UTILIZADOR",
        "visivel_para_todos": False,
        "owner_username": "paulo",
        "ativo": True,
    }
    base.update(campos)
    return SimpleNamespace(**base)


@pytest.fixture()
def dialog(_app, monkeypatch):
    from app.ui.dialogs import importar_valueset_modelo_dialog as modulo

    class _FakeSession:
        def __enter__(self):
            return None

        def __exit__(self, *_args):
            return False

    class _FakeService:
        def __init__(self, _session):
            pass

        def listar_modelos_para_separadores(self, _user_id, is_admin=False):
            utilizador = [
                _modelo(),
                _modelo(
                    id=2,
                    codigo="ROUP_STANDARD",
                    nome="RP_STD",
                    descricao="Interiores mlm Linho/frentes lacadas",
                ),
            ]
            globais = [
                _modelo(
                    id=3,
                    codigo="GLOBAL_1",
                    nome="Modelo global",
                    ambito="GLOBAL",
                    visivel_para_todos=True,
                )
            ]
            return utilizador, globais

    monkeypatch.setattr(modulo, "SessionLocal", lambda: _FakeSession())
    monkeypatch.setattr(modulo, "DefValuesetModeloService", _FakeService)

    return modulo.ImportarValuesetModeloDialog()


def _texto(table, row: int, col: int) -> str:
    item = table.item(row, col)
    return item.text() if item is not None else ""


def test_colunas_iguais_as_da_pagina(dialog) -> None:
    from app.ui.pages.def_valueset_modelos_page import DefValuesetModelosPage

    assert dialog.TABLE_HEADERS == DefValuesetModelosPage.TABLE_HEADERS


def test_mostra_descricao_observacoes_e_dono(dialog) -> None:
    table = dialog._abas["user"]["table"]

    assert table.columnCount() == 8
    assert _texto(table, 0, 0) == "ROUP_STD"
    assert _texto(table, 0, 2) == "Interiores MLM LINHO + Frentes MDF MR BRANCO B3002"
    assert _texto(table, 0, 3) == "Ferragens Standard"
    assert _texto(table, 0, 6) == "paulo"
    assert _texto(table, 0, 7) == "Sim"
    # Texto livre por inteiro na dica, para quando a coluna não chega.
    assert table.item(0, 2).toolTip().startswith("Interiores MLM LINHO")


def test_modelo_partilhado_aparece_como_global(dialog) -> None:
    table = dialog._abas["global"]["table"]

    assert _texto(table, 0, 6) == "GLOBAL"


def test_pesquisa_tambem_apanha_a_descricao(dialog) -> None:
    aba = dialog._abas["user"]
    aba["search"].setText("frentes mdf")

    assert aba["table"].rowCount() == 1
    assert _texto(aba["table"], 0, 0) == "ROUP_STD"


def test_dialogo_abre_largo(dialog) -> None:
    # Oito colunas não cabem numa janela estreita.
    assert dialog.minimumWidth() >= 1000


def test_tabela_usa_o_estilo_das_tabelas_da_app(dialog) -> None:
    import inspect

    from app.ui.dialogs.importar_valueset_modelo_dialog import (
        ImportarValuesetModeloDialog,
    )

    fonte = inspect.getsource(ImportarValuesetModeloDialog._build_aba)
    assert "configurar_tabela_orcamentos" in fonte

    table = dialog._abas["user"]["table"]
    # O cabeçalho castanho e as linhas alternadas vêm da folha de estilo comum.
    assert table.alternatingRowColors() is True
    assert "QHeaderView::section" in table.styleSheet()
