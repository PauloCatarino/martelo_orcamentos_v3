"""Import checks for the external order to production dialog."""

from __future__ import annotations

import inspect
import sys


def test_novo_processo_dialog_imports_and_columns() -> None:
    from app.ui.dialogs.novo_processo_dialog import (
        _COLUNAS_PHC,
        _COLUNAS_STREAMLIT,
        NovoProcessoDialog,
    )

    assert NovoProcessoDialog is not None
    assert [titulo for titulo, _chave in _COLUNAS_PHC] == [
        "Ano",
        "Nome Cliente",
        "Nome Cliente Simplex",
        "Nº Enc PHC",
        "Num PHC",
        "Ref Cliente",
        "Descrição Artigo",
        "Data Encomenda",
        "Data Entrega",
    ]
    assert [titulo for titulo, _chave in _COLUNAS_STREAMLIT] == [
        "Ano",
        "Cliente",
        "Cliente Abreviado",
        "Número",
        "Ref Cliente",
        "Designação",
        "Data Receção",
        "Data Entrega",
    ]


def test_novo_processo_dialog_uses_expected_services_and_controls() -> None:
    import app.ui.dialogs.novo_processo_dialog as dialog_module
    from app.ui.dialogs.novo_processo_dialog import NovoProcessoDialog

    source = inspect.getsource(dialog_module)
    dialog_source = inspect.getsource(NovoProcessoDialog)

    assert "query_phc_encomenda_itens" in source
    assert "query_streamlit_encomenda_itens" in source
    assert "CampoPesquisa" in source
    assert "ligar_persistencia_larguras" in source
    assert '"novo_processo_phc"' in source
    assert '"novo_processo_streamlit"' in source
    assert "QIntValidator" in source
    assert "QDialogButtonBox" in source
    assert "Criar Processo" in dialog_source
    assert "setAutoDefault(False)" in dialog_source
    assert "setDefault(False)" in dialog_source
    assert "cancel_button" in dialog_source
    assert "Encomenda de Cliente (PHC)" in dialog_source
    assert "Encomenda Cliente Final (Streamlit)" in dialog_source
    assert "setToolTip" in source


def test_origem_tab_constroi_resultado_phc_e_streamlit(monkeypatch) -> None:
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")

    from PySide6.QtWidgets import QApplication

    from app.ui.dialogs.novo_processo_dialog import (
        _COLUNAS_PHC,
        _COLUNAS_STREAMLIT,
        _OrigemTab,
    )

    app = QApplication.instance() or QApplication(sys.argv)
    assert app is not None

    tab_phc = _OrigemTab(
        origem="phc",
        colunas=_COLUNAS_PHC,
        larguras_key="teste_novo_processo_phc",
        num_enc_placeholder="Ex.: 1956",
    )
    tab_phc._linhas = [
        {
            "Ano": 2026,
            "Cliente": "Cliente PHC",
            "Cliente_Abreviado": "CLIENTE_PHC",
            "Enc_No": 402,
            "Num_PHC": 123,
            "Ref_Cliente": "REF",
            "Descricao_Artigo": "Mesa",
            "Data_Encomenda": "01-06-2026",
            "Data_Entrega": "15-06-2026",
        },
        {"Descricao_Artigo": "Mesa"},
        {"Descricao_Artigo": "Roupeiro"},
    ]
    tab_phc._render()
    phc = tab_phc.construir_resultado()

    assert phc == {
        "source": "phc",
        "ano": "2026",
        "num_enc_phc": "402",
        "nome_cliente": "Cliente PHC",
        "nome_cliente_simplex": "CLIENTE_PHC",
        "num_cliente_phc": "123",
        "ref_cliente": "REF",
        "descricao_artigos": "Mesa\nRoupeiro",
        "data_inicio": "01-06-2026",
        "data_entrega": "15-06-2026",
    }

    tab_streamlit = _OrigemTab(
        origem="streamlit",
        colunas=_COLUNAS_STREAMLIT,
        larguras_key="teste_novo_processo_streamlit",
        num_enc_placeholder="Ex.: _001 ou 001",
    )
    tab_streamlit._linhas = [
        {
            "Ano": 2026,
            "Cliente": "Cliente Final",
            "Cliente_Abreviado": "",
            "Numero": "_7",
            "RefCliente": "REF-F",
            "Designacao": "Cadeira",
            "DataRecepcao": "02-06-2026",
            "DataEntrega": "20-06-2026",
        },
        {"Designacao": "Cadeira"},
        {"Designacao": "Armario"},
    ]
    tab_streamlit._render()
    streamlit = tab_streamlit.construir_resultado()

    assert streamlit == {
        "source": "streamlit",
        "ano": "2026",
        "num_enc_phc": "_007",
        "nome_cliente": "Cliente Final",
        "nome_cliente_simplex": "Cliente Final",
        "num_cliente_phc": "",
        "ref_cliente": "REF-F",
        "descricao_artigos": "Cadeira\nArmario",
        "data_inicio": "02-06-2026",
        "data_entrega": "20-06-2026",
    }
