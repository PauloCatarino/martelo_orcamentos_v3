"""Novo Orçamento: quem vai para o PHC como cliente próprio e quem vai no 063."""

from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def dialog(_app):
    janela = NovoOrcamentoDialog()
    yield janela
    janela.close()


def _escolher(dialog, *, nome, temporario, num_phc=None):
    """Simular o que o `_escolher_cliente` grava depois de escolher um cliente."""
    dialog._cliente_id = 1
    dialog._cliente_nome = nome
    dialog._cliente_temporario = temporario
    dialog._num_cliente_phc = num_phc
    dialog._atualizar_criar_phc_disponivel()


def test_cliente_do_phc_vai_com_o_seu_numero_e_sem_nome(dialog) -> None:
    _escolher(dialog, nome="MÓVEIS J.F. VIVA", temporario=False, num_phc="35")

    num_cliente, nome = dialog._cliente_phc_da_proposta()

    assert num_cliente == "35"
    # O nome vem do PHC; não é o Martelo que o escreve.
    assert nome is None
    assert dialog.criar_phc_button.isEnabled() is True


def test_cliente_temporario_vai_no_063_com_o_nome(dialog) -> None:
    _escolher(dialog, nome="CARPINTARIA NOVA LDA", temporario=True)

    num_cliente, nome = dialog._cliente_phc_da_proposta()

    assert num_cliente == "063"
    assert nome == "CARPINTARIA NOVA LDA"
    assert dialog.criar_phc_button.isEnabled() is True
    assert "063" in dialog.proposta_phc_label.text()


def test_cliente_temporario_sem_nome_nao_pode_ir_para_o_phc(dialog) -> None:
    """Sem nome, a proposta ficaria «CONSUMIDOR FINAL» e sem dono."""
    _escolher(dialog, nome="   ", temporario=True)

    num_cliente, nome = dialog._cliente_phc_da_proposta()

    assert num_cliente is None
    assert nome is None
    assert dialog.criar_phc_button.isEnabled() is False


def test_cliente_do_phc_sem_numero_continua_bloqueado(dialog) -> None:
    _escolher(dialog, nome="CLIENTE SEM NUMERO", temporario=False, num_phc=None)

    assert dialog._cliente_phc_da_proposta() == (None, None)
    assert dialog.criar_phc_button.isEnabled() is False


def test_o_aviso_do_cliente_temporario_esta_na_confirmacao() -> None:
    import inspect

    fonte = inspect.getsource(NovoOrcamentoDialog._criar_proposta_phc)

    # Quem carrega no botão tem de perceber que a proposta vai no 063.
    assert "CONSUMIDOR FINAL" in fonte
    assert "Nome a escrever" in fonte
    assert "nome_cliente=nome_cliente" in fonte
