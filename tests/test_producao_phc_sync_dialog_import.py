"""A caixa das mudanças de estado vindas do PHC/Streamlit."""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])


def _diffs():
    return [
        {
            "id": 1,
            "codigo": "26.1001_01_01_CLIENTE",
            "num_enc_phc": "1001",
            "fonte": "PHC",
            "cliente": "Cliente 1",
            "ref_cliente": "REF-1",
            "responsavel": "Ana",
            "data_entrega": "30-09-2026",
            "estado_martelo": "Desenho",
            "estado_sugerido": "Arquivado",
            "estado_phc_raw": "7 - ARQUIVADO",
        },
        {
            "id": 2,
            "codigo": "26._118_01_01_CLIENTE",
            "num_enc_phc": "_118",
            "fonte": "Streamlit",
            "cliente": "Cliente 2",
            "ref_cliente": "",
            "responsavel": "Paulo",
            "data_entrega": "",
            "estado_martelo": "Producao",
            "estado_sugerido": "Finalizado",
            "estado_phc_raw": "Finalizada",
        },
    ]


def test_producao_phc_sync_dialog_imports_and_has_selection_api() -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    source = inspect.getsource(ProducaoPhcSyncDialog)

    assert "QDialog" in source
    assert "QTableWidget" in source
    assert "ItemIsUserCheckable" in source
    assert "Marcar todas" in source
    assert "Desmarcar todas" in source
    assert "Atualizar as marcadas" in source
    assert hasattr(ProducaoPhcSyncDialog, "_selecionar_tudo")
    assert hasattr(ProducaoPhcSyncDialog, "_desmarcar_tudo")
    assert hasattr(ProducaoPhcSyncDialog, "selecionados")


def test_as_colunas_dizem_de_quem_e_a_obra_e_de_onde_vem_o_estado() -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    dialog = ProducaoPhcSyncDialog(_diffs())
    cabecalhos = [
        dialog.table.horizontalHeaderItem(coluna).text()
        for coluna in range(dialog.table.columnCount())
    ]

    for esperada in ("Obra", "Nº Enc PHC", "Cliente", "Resp.", "Fonte"):
        assert esperada in cabecalhos


def test_vem_todas_marcadas_e_da_para_marcar_e_desmarcar() -> None:
    """O PHC não engana: se diz que a obra fechou, fechou."""
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    dialog = ProducaoPhcSyncDialog(_diffs())

    assert dialog.selecionados() == [(1, "Arquivado"), (2, "Finalizado")]

    dialog._desmarcar_tudo()
    assert dialog.selecionados() == []

    dialog._selecionar_tudo()
    assert dialog.selecionados() == [(1, "Arquivado"), (2, "Finalizado")]


def test_filtrar_por_responsavel_esconde_e_tira_da_conta() -> None:
    """Uma obra escondida não pode ser atualizada sem se ver."""
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    dialog = ProducaoPhcSyncDialog(_diffs())

    assert dialog.escolher_responsavel("Paulo") is True
    assert dialog.selecionados() == [(2, "Finalizado")]

    # Marcar todas só mexe no que está à vista.
    dialog._desmarcar_tudo()
    dialog.escolher_responsavel("Ana")
    dialog._selecionar_tudo()
    assert dialog.selecionados() == [(1, "Arquivado")]


def test_a_caixa_apresenta_se_quando_aparece_sozinha() -> None:
    """Ninguém a pediu: tem de dizer quem é e o que faz."""
    from app.ui.dialogs.producao_phc_sync_dialog import (
        APRESENTACAO,
        ProducaoPhcSyncDialog,
    )

    assert "todos os dias" in APRESENTACAO.casefold()
    assert "09h00" in APRESENTACAO
    # A promessa que o utilizador precisa de ler: o estado dele fica como está.
    assert "Desenho e a Producao" in APRESENTACAO

    automatica = ProducaoPhcSyncDialog(_diffs(), automatico=True)
    a_pedido = ProducaoPhcSyncDialog(_diffs(), automatico=False)

    assert "diário" in automatica.windowTitle()
    assert "diário" not in a_pedido.windowTitle()


def test_a_obra_que_salta_dois_estados_e_assinalada() -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import (
        ProducaoPhcSyncDialog,
        _salta_dois_estados,
    )

    assert _salta_dois_estados(
        {"estado_martelo": "Desenho", "estado_sugerido": "Arquivado"}
    )
    assert not _salta_dois_estados(
        {"estado_martelo": "Producao", "estado_sugerido": "Arquivado"}
    )

    dialog = ProducaoPhcSyncDialog(_diffs())

    assert dialog.table.item(0, 1).font().bold() is True
    assert "dois estados" in dialog.table.item(0, 1).toolTip()
    assert dialog.table.item(1, 1).font().bold() is False


def test_o_botao_de_gravar_desliga_se_ninguem_marcar_nada() -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    dialog = ProducaoPhcSyncDialog(_diffs())
    assert dialog._ok_button.isEnabled() is True

    dialog._desmarcar_tudo()
    assert dialog._ok_button.isEnabled() is False


def test_uma_linha_tirada_a_mao_deixa_de_contar() -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    dialog = ProducaoPhcSyncDialog(_diffs())
    dialog.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)

    assert dialog.selecionados() == [(2, "Finalizado")]
    assert "1 de 2" in dialog.contagem_label.text()
