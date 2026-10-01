"""Aviso da manhã de versão nova (pedido do Paulo, 01-10-2026).

Dias úteis, a partir das 9h30, uma vez por dia neste PC: se o servidor tiver
uma versão mais recente, o Martelo pergunta se quer instalar. Nunca instala
sem a pessoa carregar no botão, e antes de fechar pergunta em todos os menus
se há alterações por gravar.
"""

from __future__ import annotations

import inspect
from datetime import date, datetime
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox, QScrollArea, QStackedWidget, QWidget  # noqa: E402

from app.services.atualizacao_service import EstadoVersao  # noqa: E402
from app.ui.helpers import aviso_atualizacao as aviso  # noqa: E402

TERCA_0940 = datetime(2026, 10, 6, 9, 40)
TERCA_0915 = datetime(2026, 10, 6, 9, 15)
SABADO_1000 = datetime(2026, 10, 3, 10, 0)


@pytest.fixture(scope="module")
def app():
    aplicacao = QApplication.instance() or QApplication([])
    yield aplicacao


def _estado(*, ha=True, problema=None):
    return EstadoVersao(
        instalada="1.0.24",
        disponivel="1.0.25" if ha else "1.0.24",
        caminho_instalador=Path(r"\\SERVER_LE\Instaladores\Setup_Martelo_V3_1.0.25.exe"),
        pasta=Path(r"\\SERVER_LE\Instaladores"),
        ha_atualizacao=ha,
        problema=problema,
    )


def _aviso(app, *, agora=TERCA_0940, ultimo=None, **extra):
    guardados: list[date] = []
    objeto = aviso.AvisoAtualizacao(
        None,
        ativo=False,  # sem thread nem relógio nos testes
        ler_ultimo=lambda: ultimo,
        guardar_ultimo=guardados.append,
        agora=lambda: agora,
        **extra,
    )
    objeto.ativo = True
    objeto.guardados = guardados
    objeto.leituras = []
    objeto.pedir_leitura.connect(lambda: objeto.leituras.append(1))
    return objeto


def test_so_no_martelo_instalado(app, monkeypatch):
    monkeypatch.delattr("sys.frozen", raising=False)
    assert aviso.AvisoAtualizacao(None).ativo is False


@pytest.mark.parametrize(
    "agora,ultimo,vai",
    [
        (TERCA_0940, None, True),
        (TERCA_0940, date(2026, 10, 5), True),
        (TERCA_0940, date(2026, 10, 6), False),  # já avisou hoje
        (TERCA_0915, None, False),  # antes das 9h30
        (SABADO_1000, None, False),  # fim de semana
    ],
)
def test_uma_vez_por_dia_util_a_partir_das_930(app, agora, ultimo, vai):
    objeto = _aviso(app, agora=agora, ultimo=ultimo)
    objeto.verificar_se_e_hora()
    assert bool(objeto.leituras) is vai


def test_com_outra_caixa_aberta_espera_pelo_proximo_toque(app, monkeypatch):
    objeto = _aviso(app)
    monkeypatch.setattr(aviso.QApplication, "activeModalWidget", staticmethod(lambda: QWidget()))
    objeto.verificar_se_e_hora()
    assert objeto.leituras == []
    assert objeto.guardados == []


def test_versao_nova_pergunta_e_mais_tarde_nao_instala(app, monkeypatch):
    perguntas, instalacoes = [], []
    monkeypatch.setattr(
        aviso, "perguntar_instalar",
        lambda _p, estado, trabalho: perguntas.append((estado.disponivel, trabalho)) or False,
    )
    monkeypatch.setattr(aviso, "instalar_e_fechar", lambda *a, **k: instalacoes.append(a))
    objeto = _aviso(app, trabalho_aberto=lambda: "no orçamento 260954_01")
    objeto._ao_ler(_estado())
    assert perguntas == [("1.0.25", "no orçamento 260954_01")]
    assert instalacoes == []
    assert objeto.guardados == [TERCA_0940.date()]  # amanhã volta a lembrar


def test_instalar_agora_passa_pelo_quer_gravar_de_todos_os_menus(app, monkeypatch):
    chamadas = []
    monkeypatch.setattr(aviso, "perguntar_instalar", lambda *_a: True)
    monkeypatch.setattr(
        aviso, "instalar_e_fechar",
        lambda _p, estado, pode_fechar=None: chamadas.append((estado.disponivel, pode_fechar)),
    )
    pode_fechar = lambda: True  # noqa: E731
    objeto = _aviso(app, pode_fechar=pode_fechar)
    objeto._ao_ler(_estado())
    assert chamadas == [("1.0.25", pode_fechar)]


@pytest.mark.parametrize("estado", [_estado(ha=False), _estado(ha=False, problema="Pasta por definir")])
def test_sem_versao_nova_nao_aparece_nada(app, monkeypatch, estado):
    monkeypatch.setattr(aviso, "perguntar_instalar", lambda *_a: pytest.fail("não devia perguntar"))
    objeto = _aviso(app)
    objeto._ao_ler(estado)
    assert objeto.guardados == [TERCA_0940.date()]


def test_sem_rede_fica_no_diario_e_nao_repete_de_dez_em_dez_minutos(app, monkeypatch):
    monkeypatch.setattr(aviso, "perguntar_instalar", lambda *_a: pytest.fail("não devia perguntar"))
    objeto = _aviso(app)
    objeto._ao_falhar("servidor sem resposta")
    assert objeto.guardados == [TERCA_0940.date()]


def test_a_caixa_apresenta_se_e_mais_tarde_e_o_botao_por_defeito(app, monkeypatch):
    caixas = []

    def exec_falso(self):
        caixas.append(self)
        return 0

    monkeypatch.setattr(QMessageBox, "exec", exec_falso)
    assert aviso.perguntar_instalar(None, _estado(), "no orçamento 260954_01") is False
    [caixa] = caixas
    assert caixa.windowTitle() == aviso.TITULO
    assert "Sou o aviso de atualizações do Martelo" in caixa.text()
    assert "1.0.25" in caixa.text() and "1.0.24" in caixa.text()
    assert "no orçamento 260954_01" in caixa.informativeText()
    assert "Ajuda → «Atualizar agora…»" in caixa.informativeText()
    nomes = sorted(b.text() for b in caixa.buttons())
    assert nomes == ["Instalar agora", "Mais tarde"]
    # Aparece sozinha: um Enter de quem estava a escrever não instala.
    assert caixa.defaultButton().text() == "Mais tarde"
    assert caixa.escapeButton().text() == "Mais tarde"
    assert all(b.toolTip() for b in caixa.buttons())


def test_cancelar_no_quer_gravar_nao_instala_nada(app, monkeypatch):
    monkeypatch.setattr(
        aviso, "preparar_instalador_local", lambda _c: pytest.fail("não devia copiar")
    )
    assert aviso.instalar_e_fechar(None, _estado(), pode_fechar=lambda: False) is False


def test_instalar_copia_para_o_pc_abre_e_fecha(app, monkeypatch, tmp_path):
    passos = []
    local = tmp_path / "Setup_Martelo_V3_1.0.25.exe"
    monkeypatch.setattr(aviso, "preparar_instalador_local", lambda c: passos.append("copiar") or local)
    monkeypatch.setattr(aviso.os, "startfile", lambda c: passos.append(("abrir", c)), raising=False)
    monkeypatch.setattr(aviso.QGuiApplication, "quit", staticmethod(lambda: passos.append("fechar")))
    assert aviso.instalar_e_fechar(None, _estado(), pode_fechar=lambda: passos.append("gravar?") or True)
    assert passos == ["gravar?", "copiar", ("abrir", str(local)), "fechar"]


def test_a_ajuda_usa_a_mesma_passagem():
    from app.ui.pages.ajuda_page import AjudaPage

    fonte = inspect.getsource(AjudaPage._atualizar_martelo)
    assert "instalar_e_fechar(" in fonte
    assert "pode_fechar_tudo" in fonte


# --- «Quer gravar?» ao mudar de menu / fechar: perguntava à QScrollArea. ---

class _PaginaComAlteracoes(QWidget):
    def __init__(self, resposta):
        super().__init__()
        self.resposta = resposta
        self.perguntas = 0

    def pode_sair(self):
        self.perguntas += 1
        return self.resposta


def test_a_pagina_atual_e_a_de_dentro_da_caixa_de_deslocamento(app):
    from app.ui.main_window import MainWindow

    janela = type("Janela", (), {})()
    janela.pages = QStackedWidget()
    pagina = _PaginaComAlteracoes(True)
    caixa = QScrollArea()
    caixa.setWidget(pagina)
    janela.pages.addWidget(caixa)
    assert MainWindow._pagina_atual(janela) is pagina


def test_pode_fechar_tudo_pergunta_a_todos_os_menus(app):
    from app.ui.main_window import MainWindow

    janela = type("Janela", (), {})()
    sim, nao = _PaginaComAlteracoes(True), _PaginaComAlteracoes(False)
    janela._pages_by_name = {"inicio": QWidget(), "producao": sim, "outra": nao}
    assert MainWindow.pode_fechar_tudo(janela) is False
    assert sim.perguntas == 1 and nao.perguntas == 1
    nao.resposta = True
    assert MainWindow.pode_fechar_tudo(janela) is True


def test_mudar_de_menu_e_fechar_perguntam_a_pagina_e_nao_a_caixa():
    from app.ui.main_window import MainWindow

    for metodo in (MainWindow.show_page, MainWindow.closeEvent):
        fonte = inspect.getsource(metodo)
        assert "self._pagina_atual()" in fonte
        assert "self.pages.currentWidget()" not in fonte
