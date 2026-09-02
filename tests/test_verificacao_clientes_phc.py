"""Aviso diário de clientes novos/editados no PHC (parte Qt)."""

from __future__ import annotations

import inspect
import sys

import pytest
from PySide6.QtWidgets import QApplication

from app.repositories.cliente_repository import DiferencasPHC
from app.ui.helpers import verificacao_clientes_phc as modulo
from app.ui.helpers.verificacao_clientes_phc import VerificadorClientesPHC


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def verificador(_app):
    objeto = VerificadorClientesPHC(user_id=1, ativo=False)
    yield objeto
    objeto.parar()


def test_mensagem_diz_quantos_e_quais() -> None:
    diferencas = DiferencasPHC(
        novos=("300 — Cliente Novo",), alterados=("200 — Nome Novo",)
    )

    mensagem = VerificadorClientesPHC.mensagem_diferencas(diferencas)

    assert "Clientes novos: 1" in mensagem
    assert "300 — Cliente Novo" in mensagem
    assert "Clientes editados: 1" in mensagem
    assert "200 — Nome Novo" in mensagem
    assert "Quer atualizar agora" in mensagem


def test_mensagem_resume_quando_sao_muitos() -> None:
    novos = tuple(f"{n} — Cliente {n}" for n in range(20))

    mensagem = VerificadorClientesPHC.mensagem_diferencas(
        DiferencasPHC(novos=novos, alterados=())
    )

    assert "Clientes novos: 20" in mensagem
    assert "e mais 12" in mensagem


def test_desligado_nao_vai_ao_phc(verificador) -> None:
    pedidos: list[int] = []
    verificador.pedir_verificacao.connect(lambda: pedidos.append(1))

    verificador.verificar_se_e_hora()

    assert pedidos == []


def test_quando_e_hora_pede_a_verificacao_e_marca_o_dia(monkeypatch, _app) -> None:
    objeto = VerificadorClientesPHC(user_id=1, ativo=True)
    dias: list[object] = []
    monkeypatch.setattr(modulo.agenda_clientes_phc, "deve_verificar", lambda *a: True)
    monkeypatch.setattr(objeto, "_ultima_verificacao", lambda: None)
    monkeypatch.setattr(objeto, "_guardar_verificacao", dias.append)
    pedidos: list[int] = []
    objeto.pedir_verificacao.connect(lambda: pedidos.append(1))

    objeto.verificar_se_e_hora()
    # Segunda passagem: já está a trabalhar, não repete o pedido.
    objeto.verificar_se_e_hora()

    assert pedidos == [1]
    assert len(dias) == 1
    objeto.parar()


def test_sem_novidades_nao_incomoda_o_utilizador(monkeypatch, verificador) -> None:
    chamadas: list[int] = []
    monkeypatch.setattr(
        modulo.QMessageBox, "question", lambda *a, **k: chamadas.append(1)
    )

    verificador._on_verificado(DiferencasPHC(novos=(), alterados=()))

    assert chamadas == []


def test_falha_do_phc_fica_no_diario_e_nao_abre_janelas(
    monkeypatch, verificador
) -> None:
    registados: list[str] = []
    monkeypatch.setattr(modulo.diario_bordo, "registar_erro", registados.append)
    monkeypatch.setattr(
        modulo.QMessageBox,
        "warning",
        lambda *a, **k: pytest.fail("a verificação automática não deve avisar"),
    )

    verificador._on_falhou("sem ligação ao PHC")

    assert registados and "sem ligação ao PHC" in registados[0]


def test_main_window_liga_o_verificador_ao_menu_clientes() -> None:
    from app.ui.main_window import MainWindow

    fonte = inspect.getsource(MainWindow.__init__)
    assert "VerificadorClientesPHC(" in fonte
    # Só quem tem o menu Clientes é incomodado com o aviso.
    assert 'ativo=self._permissions.get("menu.clientes", False)' in fonte
    assert "clientes_atualizados.connect" in fonte
