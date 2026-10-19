"""Novo Orçamento › Orçamento antigo: escolher a versão (19-10-2026).

O 260186 (INNERE) tem as versões 01 a 05 no servidor, feitas no Martelo V2. Ao
escolher a pasta, a janela tem de propor a 06 e não deixar gravar por cima
de uma versão do V2 que já tem ficheiros.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox

from app.ui.dialogs import novo_orcamento_dialog as modulo
from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def dialog(_app):
    janela = NovoOrcamentoDialog()
    janela.antigo_checkbox.setChecked(True)
    yield janela
    janela.close()


@pytest.fixture()
def pasta_innere(tmp_path) -> Path:
    mae = tmp_path / "2026" / "260186_INNERE"
    for versao in ("01", "02", "03", "04", "05"):
        (mae / versao).mkdir(parents=True)
        (mae / versao / f"260186_{versao}.pdf").write_text("v2", encoding="utf-8")
    (mae / "PDF").mkdir()
    return mae


def test_escolher_a_pasta_propoe_a_versao_seguinte(dialog, pasta_innere) -> None:
    dialog._usar_pasta(pasta_innere.as_posix())

    assert dialog.versao_input.value() == 6
    assert dialog.versao_input.text() == "06"
    assert dialog.num_orcamento_input.text() == "260186"
    assert "260186_INNERE/06" in dialog.versao_info_label.text()
    assert "01, 02, 03, 04, 05" in dialog.versao_info_label.text()

    dados = dialog.get_data()
    assert dados.numero_versao == 6
    assert dados.pasta_manual == pasta_innere.as_posix()


def test_escolher_a_pasta_de_uma_versao_sobe_para_a_mae(
    dialog, pasta_innere
) -> None:
    dialog._usar_pasta((pasta_innere / "05").as_posix())

    assert Path(dialog.get_data().pasta_manual) == pasta_innere
    assert dialog.versao_input.value() == 6
    assert "versão 05" in dialog.pasta_label.text()


def test_numero_ja_escrito_nao_e_trocado_pela_pasta(dialog, pasta_innere) -> None:
    dialog.num_orcamento_input.setText("260466")

    dialog._usar_pasta(pasta_innere.as_posix())

    assert dialog.num_orcamento_input.text() == "260466"


def test_versao_do_v2_com_ficheiros_nao_deixa_gravar(dialog, pasta_innere) -> None:
    dialog._usar_pasta(pasta_innere.as_posix())
    dialog.versao_input.setValue(5)

    assert "já existe" in dialog.versao_info_label.text()
    erro = dialog._erro_versao_ocupada(dialog.get_data())

    assert erro is not None
    assert "05" in erro
    assert "a seguinte é a 06" in erro


def test_versao_nova_ou_pasta_vazia_deixa_gravar(dialog, pasta_innere) -> None:
    dialog._usar_pasta(pasta_innere.as_posix())

    assert dialog._erro_versao_ocupada(dialog.get_data()) is None

    (pasta_innere / "06").mkdir()
    assert dialog._erro_versao_ocupada(dialog.get_data()) is None


def test_numero_diferente_do_da_pasta_pergunta_antes(
    monkeypatch, dialog, tmp_path
) -> None:
    """O caso 260466 ligado à pasta 260446_JF_VIVA."""
    pasta = tmp_path / "2026" / "260446_JF_VIVA"
    pasta.mkdir(parents=True)
    perguntas: list[str] = []

    def _perguntar(_pai, _titulo, texto, *args, **kwargs):
        perguntas.append(texto)
        return QMessageBox.StandardButton.No

    monkeypatch.setattr(modulo.QMessageBox, "question", _perguntar)
    dialog.num_orcamento_input.setText("260466")
    dialog._usar_pasta(pasta.as_posix())

    assert dialog._confirmar_numero_da_pasta(dialog.get_data()) is False
    assert "260466" in perguntas[0]
    assert "260446_JF_VIVA" in perguntas[0]


def test_numero_igual_ao_da_pasta_nao_pergunta(
    monkeypatch, dialog, pasta_innere
) -> None:
    def _nao_devia_perguntar(*_args, **_kwargs):
        raise AssertionError("não devia perguntar")

    monkeypatch.setattr(modulo.QMessageBox, "question", _nao_devia_perguntar)
    dialog._usar_pasta(pasta_innere.as_posix())

    assert dialog._confirmar_numero_da_pasta(dialog.get_data()) is True


def test_orcamento_normal_nao_leva_versao(_app) -> None:
    janela = NovoOrcamentoDialog()
    try:
        assert janela.get_data().numero_versao is None
    finally:
        janela.close()
