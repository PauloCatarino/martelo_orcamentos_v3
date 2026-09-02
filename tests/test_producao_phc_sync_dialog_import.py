"""A caixa das mudanças de estado vindas do PHC/Streamlit."""

from __future__ import annotations

import inspect
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

_app = QApplication.instance() or QApplication([])

from app.ui.dialogs.producao_phc_sync_dialog import CHAVE_LARGURAS


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


def _limpar_larguras_guardadas() -> None:
    """Sem sessão, as larguras guardam-se em "default" — é esse o resíduo."""
    from PySide6.QtCore import QSettings

    settings = QSettings("Lanca Encanto", "Martelo Orcamentos V3")
    for chave in settings.allKeys():
        if CHAVE_LARGURAS in chave and "/default/" in chave:
            settings.remove(chave)
    settings.sync()


@pytest.fixture()
def sem_larguras_guardadas():
    _limpar_larguras_guardadas()
    yield
    _limpar_larguras_guardadas()


def test_as_larguras_de_arranque_nao_deixam_uma_coluna_comer_o_ecra(
    sem_larguras_guardadas,
) -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import (
        LARGURA_MAXIMA_SEMEADA,
        LARGURA_VISTOS,
        ProducaoPhcSyncDialog,
    )

    diffs = _diffs()
    diffs[0]["cliente"] = "GOSIMAT- COMERCIO E INDUSTRIA DE MATERIAIS DE " * 3
    dialog = ProducaoPhcSyncDialog(diffs)
    cabecalho = dialog.table.horizontalHeader()
    larguras = [
        cabecalho.sectionSize(coluna)
        for coluna in range(dialog.table.columnCount())
    ]

    assert larguras[0] == LARGURA_VISTOS
    assert max(larguras) <= LARGURA_MAXIMA_SEMEADA


def test_as_larguras_de_arranque_nao_se_gravam_sozinhas(
    sem_larguras_guardadas,
) -> None:
    """Só o que o utilizador arrasta é que fica guardado.

    Se as larguras de arranque se gravassem, passavam a contar como escolha
    dele e o programa nunca mais as podia melhorar.
    """
    from PySide6.QtCore import QSettings

    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    ProducaoPhcSyncDialog(_diffs())

    settings = QSettings("Lanca Encanto", "Martelo Orcamentos V3")
    guardadas = [
        chave
        for chave in settings.allKeys()
        if CHAVE_LARGURAS in chave and "/default/" in chave
    ]

    assert guardadas == []


def test_o_que_o_utilizador_arrasta_fica_guardado(sem_larguras_guardadas) -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    primeiro = ProducaoPhcSyncDialog(_diffs())
    primeiro.table.horizontalHeader().resizeSection(1, 321)

    segundo = ProducaoPhcSyncDialog(_diffs())

    assert segundo.table.horizontalHeader().sectionSize(1) == 321


def test_a_janela_abre_larga_para_caber_tudo(sem_larguras_guardadas) -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import (
        LARGURA_MINIMA,
        ProducaoPhcSyncDialog,
    )

    dialog = ProducaoPhcSyncDialog(_diffs())
    desejada = dialog._largura_desejada()
    ecra = dialog.screen()

    # Nunca maior do que o ecrã: uma caixa que não cabe não se consegue fechar.
    assert ecra is None or desejada <= ecra.availableGeometry().width()
    if ecra is None or ecra.availableGeometry().width() >= LARGURA_MINIMA:
        assert desejada >= LARGURA_MINIMA


def test_o_espaco_que_sobra_vai_para_o_nome_do_cliente(
    sem_larguras_guardadas,
) -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import (
        COLUNA_CLIENTE,
        ProducaoPhcSyncDialog,
    )

    dialog = ProducaoPhcSyncDialog(_diffs())
    # Uma tabela larguíssima: as colunas não chegam ao fim e sobra espaço.
    dialog.table.resize(3000, 400)
    _app.processEvents()  # o viewport só sabe a largura depois do layout
    cabecalho = dialog.table.horizontalHeader()
    antes = cabecalho.sectionSize(COLUNA_CLIENTE)

    dialog._dar_o_resto_ao_cliente()

    assert cabecalho.sectionSize(COLUNA_CLIENTE) > antes


def test_uma_linha_tirada_a_mao_deixa_de_contar() -> None:
    from app.ui.dialogs.producao_phc_sync_dialog import ProducaoPhcSyncDialog

    dialog = ProducaoPhcSyncDialog(_diffs())
    dialog.table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)

    assert dialog.selecionados() == [(2, "Finalizado")]
    assert "1 de 2" in dialog.contagem_label.text()
