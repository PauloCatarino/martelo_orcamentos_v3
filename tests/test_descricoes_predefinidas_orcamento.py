"""Descrições pré-definidas também no Info 1 / Info 2 do orçamento.

O Paulo usa o Info 1 e o Info 2 para dizer os materiais do orçamento
("INTERIORES MLM LINHO CANCUN", "FRENTES MDF BRANCO"). Esses textos já estão
nas descrições pré-definidas dos items: o mesmo menu passa a abrir-se a partir
do Novo Orçamento e do Editar Orçamento, e escreve linhas simples (sem o
tabulador e o marcador que levam na descrição do item).
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QTextEdit

from app.core.session import app_session
from app.ui.dialogs import descricoes_predefinidas_dialog as modulo_dialogo
from app.ui.dialogs.descricoes_predefinidas_dialog import (
    DescricaoEscolhida,
    DescricoesPredefinidasDialog,
)
from app.ui.widgets import campo_descricoes_predefinidas as modulo_campo
from app.ui.widgets.campo_descricoes_predefinidas import (
    acrescentar_linhas,
    linhas_para_info,
)


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def utilizador(monkeypatch):
    monkeypatch.setattr(app_session, "current_user", SimpleNamespace(id=5))


@dataclass
class _Linha:
    id: int
    texto: str
    tipo: str = "-"
    ordem: int = 1


class _MenuFalso:
    """Faz de conta que a pessoa marcou estas descrições e carregou «Inserir»."""

    escolhidas: list[DescricaoEscolhida] = []
    aberto_com: dict = {}

    def __init__(self, parent=None, *, user_id=None, destino=None) -> None:
        type(self).aberto_com = {"user_id": user_id, "destino": destino}

    def exec(self) -> int:
        return 1

    def checked_entries(self) -> list[DescricaoEscolhida]:
        return list(self.escolhidas)


@pytest.fixture()
def menu_falso(monkeypatch):
    _MenuFalso.escolhidas = [
        DescricaoEscolhida(1, "Interiores AGL MLM LINHO CANCUN 10/16/19mm", "-"),
        DescricaoEscolhida(2, "Frentes MDF HIDROFUGO BRANCO B3002/MA_19MM", "-"),
    ]
    _MenuFalso.aberto_com = {}
    monkeypatch.setattr(modulo_dialogo, "DescricoesPredefinidasDialog", _MenuFalso)
    return _MenuFalso


# -- O texto que entra no campo ------------------------------------------------


def test_no_info_as_descricoes_entram_sem_marcador_nem_tabulador() -> None:
    entries = [
        DescricaoEscolhida(1, "Interiores AGL MLM LINHO CANCUN", "-"),
        DescricaoEscolhida(2, "  Puxador Aplicar   (NAO INCLUI) ", "*"),
        DescricaoEscolhida(3, "   ", "-"),
    ]

    assert linhas_para_info(entries) == [
        "Interiores AGL MLM LINHO CANCUN",
        "Puxador Aplicar (NAO INCLUI)",
    ]


def test_acrescenta_no_fim_numa_linha_nova(_app) -> None:
    campo = QTextEdit()
    campo.setPlainText("INTERIORES MLM LINHO CANCUN")

    inseridas = acrescentar_linhas(campo, ["Frentes MDF BRANCO", "Puxador Fresado 'J'"])

    assert inseridas == 2
    assert campo.toPlainText() == (
        "INTERIORES MLM LINHO CANCUN\nFrentes MDF BRANCO\nPuxador Fresado 'J'"
    )


def test_campo_vazio_fica_so_com_as_descricoes(_app) -> None:
    campo = QTextEdit()

    acrescentar_linhas(campo, ["Frentes MDF BRANCO"])

    assert campo.toPlainText() == "Frentes MDF BRANCO"


def test_linha_que_o_campo_ja_tem_nao_se_repete(_app) -> None:
    campo = QTextEdit()
    campo.setPlainText("FRENTES MDF BRANCO\n")

    inseridas = acrescentar_linhas(
        campo, ["Frentes MDF Branco", "Pes AXILO", "Pes AXILO"]
    )

    assert inseridas == 1
    assert campo.toPlainText() == "FRENTES MDF BRANCO\nPes AXILO"


# -- Novo Orçamento -------------------------------------------------------------


def test_novo_orcamento_tem_o_botao_no_info_1_e_no_info_2(_app) -> None:
    from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog

    dialog = NovoOrcamentoDialog()
    try:
        for botao, campo in (
            (dialog.info_1_descricoes_button, "Info 1"),
            (dialog.info_2_descricoes_button, "Info 2"),
        ):
            assert botao.text() == "Descrições…"
            assert campo in botao.toolTip()
            # O Enter com o foco no botão não pode reabrir o menu.
            assert botao.autoDefault() is False
        assert dialog.info_1_input.toolTip()
        assert dialog.info_2_input.toolTip()
    finally:
        dialog.close()


def test_novo_orcamento_insere_as_marcadas_no_info_1(
    _app, utilizador, menu_falso
) -> None:
    from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog

    dialog = NovoOrcamentoDialog()
    try:
        dialog.info_1_descricoes_button.click()

        assert menu_falso.aberto_com == {"user_id": 5, "destino": "Info 1"}
        assert dialog.info_1_input.toPlainText() == (
            "Interiores AGL MLM LINHO CANCUN 10/16/19mm\n"
            "Frentes MDF HIDROFUGO BRANCO B3002/MA_19MM"
        )
        assert dialog.info_2_input.toPlainText() == ""
        assert dialog.get_data().info_1.startswith("Interiores AGL MLM")
    finally:
        dialog.close()


def test_sem_utilizador_avisa_e_nao_abre_o_menu(_app, monkeypatch, menu_falso) -> None:
    from app.ui.dialogs.novo_orcamento_dialog import NovoOrcamentoDialog

    avisos: list[str] = []
    monkeypatch.setattr(app_session, "current_user", None)
    monkeypatch.setattr(
        modulo_campo.QMessageBox,
        "warning",
        lambda _pai, _titulo, texto, *a, **k: avisos.append(texto),
    )
    dialog = NovoOrcamentoDialog()
    try:
        dialog.info_2_descricoes_button.click()

        assert avisos and "Utilizador não identificado" in avisos[0]
        assert menu_falso.aberto_com == {}
        assert dialog.info_2_input.toPlainText() == ""
    finally:
        dialog.close()


# -- Editar Orçamento -----------------------------------------------------------


def test_editar_orcamento_insere_as_marcadas_no_info_2(
    _app, monkeypatch, utilizador, menu_falso
) -> None:
    from app.ui.dialogs.editar_orcamento_dialog import (
        EditarOrcamentoDialog,
        EditarOrcamentoDialogData,
    )

    monkeypatch.setattr(
        EditarOrcamentoDialog, "_carregar_utilizadores", lambda self: None
    )
    dados = EditarOrcamentoDialogData(
        obra="",
        descricao=None,
        localizacao=None,
        ref_cliente=None,
        estado="Enviado",
        info_2="ROUPEIROS",
    )
    dialog = EditarOrcamentoDialog(None, dados)
    try:
        assert dialog.info_1_descricoes_button.autoDefault() is False
        dialog.info_2_descricoes_button.click()

        assert menu_falso.aberto_com["destino"] == "Info 2"
        assert dialog.get_data().info_2 == (
            "ROUPEIROS\n"
            "Interiores AGL MLM LINHO CANCUN 10/16/19mm\n"
            "Frentes MDF HIDROFUGO BRANCO B3002/MA_19MM"
        )
        assert dialog.get_data().info_1 is None
    finally:
        dialog.close()


# -- O menu em si -----------------------------------------------------------------


class _SessaoFalsa:
    def __enter__(self):
        return self

    def __exit__(self, *exc) -> bool:
        return False


@pytest.fixture()
def lista_falsa(monkeypatch):
    linhas = [
        _Linha(1, "Interiores AGL MLM LINHO CANCUN 10/16/19mm"),
        _Linha(2, "Frentes MDF HIDROFUGO BRANCO B3002/MA_19MM"),
        _Linha(3, "Puxador Aplicar (NAO INCLUI)", "*"),
    ]

    class _ServicoFalso:
        def __init__(self, _session) -> None:
            pass

        def listar(self, _user_id):
            return list(linhas)

        def criar(self, _user_id, texto, tipo):
            linhas.append(_Linha(len(linhas) + 1, texto, tipo))

    monkeypatch.setattr(modulo_dialogo, "SessionLocal", _SessaoFalsa)
    monkeypatch.setattr(modulo_dialogo, "DescricaoPredefinidaService", _ServicoFalso)
    return linhas


def test_o_menu_diz_para_onde_vai_o_texto(_app, lista_falsa) -> None:
    dialog = DescricoesPredefinidasDialog(None, user_id=5, destino="Info 1")
    try:
        assert dialog.windowTitle() == "Descrições pré-definidas → Info 1"
        assert "«Info 1»" in dialog.btn_insert.toolTip()
        assert "Marque" in dialog.status_label.text()

        dialog.lista.item(0).setCheckState(Qt.CheckState.Checked)
        dialog.lista.item(2).setCheckState(Qt.CheckState.Checked)

        assert dialog.status_label.text().startswith("2 descrições marcadas")
        assert "«Info 1»" in dialog.status_label.text()
    finally:
        dialog.close()


def test_sem_destino_o_titulo_fica_como_era(_app, lista_falsa) -> None:
    dialog = DescricoesPredefinidasDialog(None, user_id=5)
    try:
        assert dialog.windowTitle() == "Descrições pré-definidas"
    finally:
        dialog.close()


def test_adicionar_uma_descricao_nao_tira_as_marcas(_app, lista_falsa) -> None:
    dialog = DescricoesPredefinidasDialog(None, user_id=5, destino="Info 1")
    try:
        dialog.lista.item(1).setCheckState(Qt.CheckState.Checked)

        dialog._executar(lambda s: modulo_dialogo.DescricaoPredefinidaService(s).criar(
            5, "Frentes AGL MLM CINZA L166/SC 19mm", "-"
        ))

        assert dialog.lista.count() == 4
        assert [e.id for e in dialog.checked_entries()] == [2]
        assert dialog.status_label.text().startswith("1 descrição marcada")
    finally:
        dialog.close()


def test_todos_os_botoes_do_menu_tem_dica(_app, lista_falsa) -> None:
    dialog = DescricoesPredefinidasDialog(None, user_id=5, destino="Info 2")
    try:
        for botao in (
            dialog.btn_add,
            dialog.btn_edit,
            dialog.btn_remove,
            dialog.btn_up,
            dialog.btn_down,
            dialog.btn_insert,
            dialog.btn_cancel,
            dialog.edit_search,
        ):
            assert botao.toolTip(), botao
    finally:
        dialog.close()
