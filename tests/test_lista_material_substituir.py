"""Lista Material_IMOS: abrir a que existe, ou fazer uma nova por cima.

Antes, quando a lista já existia, o Martelo só perguntava "pretende abrir?" —
quem quisesse refazê-la tinha de ir apagar o ficheiro à mão no servidor. Pedido
do Paulo (2026-08-31): passar a haver escolha entre abrir e criar de novo.

A substituição merece cuidado: a Lista Material leva trabalho à mão por cima do
que o Martelo gera, e o Excel é conduzido por fora (COM/PowerShell), o que pode
falhar a meio. Por isso a lista antiga sai da frente ANTES de se escrever a
nova, e volta ao lugar se a geração falhar.
"""

from __future__ import annotations

import inspect
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.ui.pages.producao_page import ProducaoPage

_app = QApplication.instance() or QApplication([])

NOME = "Lista_Material_0964_02_26_JOEL_OLIVEIRA.xlsm"


def _lista(tmp_path: Path, conteudo: str = "trabalho feito à mão") -> Path:
    caminho = tmp_path / NOME
    caminho.write_text(conteudo, encoding="utf8")
    return caminho


# ----- pôr de lado / repor -----


def test_a_lista_antiga_sai_da_frente_com_data_e_hora(tmp_path: Path) -> None:
    lista = _lista(tmp_path)

    guardada = ProducaoPage._por_a_lista_de_lado(lista)

    assert not lista.exists()  # o lugar ficou livre para a nova
    assert guardada.exists()
    assert guardada.read_text(encoding="utf8") == "trabalho feito à mão"
    assert "_substituida_" in guardada.name
    assert guardada.suffix == ".xlsm"
    assert guardada.parent == lista.parent  # fica na pasta da obra


def test_duas_substituicoes_nao_se_atropelam(tmp_path: Path) -> None:
    primeira = ProducaoPage._por_a_lista_de_lado(_lista(tmp_path, "versão 1"))
    segunda = ProducaoPage._por_a_lista_de_lado(_lista(tmp_path, "versão 2"))

    assert primeira.exists() and segunda.exists()
    assert primeira.read_text(encoding="utf8") == "versão 1"


def test_se_a_geracao_falhar_a_lista_antiga_volta_ao_lugar(tmp_path: Path) -> None:
    """Sem isto, quem substituía ficava sem a antiga E sem a nova."""
    lista = _lista(tmp_path)
    guardada = ProducaoPage._por_a_lista_de_lado(lista)

    reposta = ProducaoPage._repor_lista_guardada(guardada, lista)

    assert reposta is True
    assert lista.exists()
    assert lista.read_text(encoding="utf8") == "trabalho feito à mão"
    assert not guardada.exists()


def test_repor_por_cima_de_um_ficheiro_meio_escrito(tmp_path: Path) -> None:
    """O Excel pode ter deixado um ficheiro a meio antes de rebentar."""
    lista = _lista(tmp_path)
    guardada = ProducaoPage._por_a_lista_de_lado(lista)
    lista.write_text("lixo de uma geração falhada", encoding="utf8")

    assert ProducaoPage._repor_lista_guardada(guardada, lista) is True
    assert lista.read_text(encoding="utf8") == "trabalho feito à mão"


def test_repor_sem_nada_guardado_nao_faz_nada(tmp_path: Path) -> None:
    """Quem não estava a substituir não tem nada para repor."""
    assert ProducaoPage._repor_lista_guardada(None, tmp_path / NOME) is False
    assert (
        ProducaoPage._repor_lista_guardada(tmp_path / "nao_existe.xlsm", tmp_path / NOME)
        is False
    )


# ----- a escolha -----


def test_a_janela_da_escolha_tem_as_tres_saidas() -> None:
    fonte = inspect.getsource(ProducaoPage._escolher_o_que_fazer_a_lista)

    assert "Abrir a lista existente" in fonte
    assert "Criar nova (substitui a atual)" in fonte
    assert "Cancelar" in fonte
    # Abrir é o que se faz quase sempre: é o botão por omissão.
    assert "setDefaultButton(abrir_button)" in fonte
    # E substituir pede uma segunda confirmação, com o "Não" por omissão.
    assert "QMessageBox.StandardButton.No,\n        )" in fonte


def test_a_confirmacao_diz_o_que_se_perde_e_o_que_fica() -> None:
    fonte = inspect.getsource(ProducaoPage._escolher_o_que_fazer_a_lista)

    assert "à mão" in fonte  # o que se perde
    assert "não é apagada" in fonte  # e que a antiga fica lá


def test_o_fluxo_liga_a_escolha_ao_resto() -> None:
    fonte = inspect.getsource(ProducaoPage._lista_material_imos)

    # Abrir e cancelar saem já; só "substituir" segue para a criação.
    assert '== "abrir"' in fonte
    assert '!= "substituir"' in fonte
    # A antiga sai da frente antes de gerar, e volta se a geração falhar.
    assert fonte.index("_por_a_lista_de_lado") < fonte.index(
        "execute_lista_material_imos"
    )
    assert "_repor_lista_guardada" in fonte
