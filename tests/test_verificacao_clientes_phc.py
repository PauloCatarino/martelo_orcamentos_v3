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


def test_mensagem_apresenta_se_e_diz_quantos_e_quais() -> None:
    diferencas = DiferencasPHC(
        novos=("300 — Cliente Novo",), alterados=("200 — Nome Novo",)
    )

    mensagem = VerificadorClientesPHC.mensagem_diferencas(diferencas)

    # A caixa aparece sozinha: tem de dizer quem fala, o que faz e quando.
    assert "analisador diário dos clientes do PHC" in mensagem
    assert "dias úteis, às 09h00" in mensagem
    assert "Clientes novos: 1" in mensagem
    assert "300 — Cliente Novo" in mensagem
    assert "Clientes editados: 1" in mensagem
    assert "200 — Nome Novo" in mensagem
    assert "atualize agora a tabela de clientes do Martelo" in mensagem
    # E deixar claro que o PHC não é tocado.
    assert "No PHC só leio" in mensagem


def test_mensagem_resume_quando_sao_muitos() -> None:
    novos = tuple(f"{n} — Cliente {n}" for n in range(20))

    mensagem = VerificadorClientesPHC.mensagem_diferencas(
        DiferencasPHC(novos=novos, alterados=())
    )

    assert "Clientes novos: 20" in mensagem
    assert "e mais 12" in mensagem


def test_lista_completa_vai_para_os_detalhes_so_quando_sao_muitos() -> None:
    poucos = DiferencasPHC(novos=("300 — Cliente Novo",), alterados=())
    # Poucos: a caixa já os mostra todos, não há detalhes a esconder.
    assert VerificadorClientesPHC.detalhe_diferencas(poucos) == ""

    muitos = DiferencasPHC(
        novos=tuple(f"{n} — Cliente {n}" for n in range(20)),
        alterados=("200 — Nome Novo",),
    )
    detalhe = VerificadorClientesPHC.detalhe_diferencas(muitos)

    assert "CLIENTES NOVOS:" in detalhe
    assert "CLIENTES EDITADOS:" in detalhe
    # Lá dentro estão TODOS, incluindo os que a caixa resumiu.
    for n in range(20):
        assert f"{n} — Cliente {n}" in detalhe
    assert "200 — Nome Novo" in detalhe


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
    caixas: list[int] = []
    monkeypatch.setattr(
        modulo.QMessageBox, "exec", lambda self: caixas.append(1)
    )

    verificador._on_verificado(DiferencasPHC(novos=(), alterados=()))

    assert caixas == []


def test_com_novidades_pergunta_com_botoes_em_portugues(
    monkeypatch, verificador
) -> None:
    vistas: list[object] = []

    def _mostrar(caixa):
        vistas.append(caixa)
        return 0

    monkeypatch.setattr(modulo.QMessageBox, "exec", _mostrar)
    pedidos: list[int] = []
    verificador.pedir_sincronizacao.connect(lambda: pedidos.append(1))

    verificador._on_verificado(
        DiferencasPHC(novos=("300 — Cliente Novo",), alterados=())
    )

    assert len(vistas) == 1
    rotulos = [botao.text() for botao in vistas[0].buttons()]
    assert rotulos == ["Sim, atualizar agora", "Agora não"]
    assert vistas[0].windowTitle() == modulo.TITULO
    # Ninguém carregou em nada (o exec foi substituído): não sincroniza.
    assert pedidos == []


def test_responder_sim_manda_sincronizar(monkeypatch, verificador) -> None:
    def _carregar_no_sim(caixa):
        caixa.setDefaultButton(caixa.buttons()[0])
        caixa.buttons()[0].click()
        return 0

    monkeypatch.setattr(modulo.QMessageBox, "exec", _carregar_no_sim)
    pedidos: list[int] = []
    verificador.pedir_sincronizacao.connect(lambda: pedidos.append(1))

    verificador._on_verificado(
        DiferencasPHC(novos=("300 — Cliente Novo",), alterados=())
    )

    assert pedidos == [1]


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
