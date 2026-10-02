"""Registo de Horas: editor do dia, página, envio do mês, avisos e menu."""

from __future__ import annotations

import inspect
from datetime import date, datetime

import pytest
from PySide6.QtCore import QTime
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget
from sqlalchemy import BigInteger, create_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base
from app.domain import registo_horas as r
from app.models import User, UserPermission
from app.services.email_service import EmailConfig
from app.services.permission_service import (
    DEFAULT_USER_PERMISSIONS,
    DESCRICOES_ACESSOS,
    MENU_PERMISSIONS,
)
from app.services.registo_horas_service import RegistoHorasService
from app.ui.dialogs import registo_horas_envio_dialog as envio_mod
from app.ui.dialogs.registo_horas_dia_dialog import RegistoHorasDiaDialog
from app.ui.dialogs.registo_horas_envio_dialog import RegistoHorasEnvioDialog, corpo_html
from app.ui.helpers import registo_horas_acoes as acoes
from app.ui.helpers import registo_horas_avisos as avisos
from app.ui.pages import registo_horas_page as pagina_mod

_app = QApplication.instance() or QApplication([])


@compiles(BigInteger, "sqlite")
def _bigint(type_, compiler, **kw):  # noqa: ANN001
    return "INTEGER"


@pytest.fixture()
def base(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    fabrica = sessionmaker(bind=engine)
    with fabrica() as s:
        for uid, nome, role in ((1, "Administrador Martelo", "admin"), (2, "Paulo Catarino", "user"),
                                (11, "Pedro", "user")):
            s.add(User(id=uid, username=nome.split()[0].lower(), nome=nome, email=f"{uid}@x.pt",
                       password_hash="x", role=role))
        s.add(UserPermission(user_id=11, permission_key="menu.registo_horas", enabled=True))
        s.commit()
    for modulo in (pagina_mod, acoes, avisos):
        monkeypatch.setattr(modulo, "SessionLocal", fabrica)
    monkeypatch.setattr(pagina_mod.diario_bordo, "registar_acao", lambda *_a, **_k: None)
    yield fabrica
    engine.dispose()


# ---- editor de um dia ------------------------------------------------------------
class _Folha:
    def __init__(self):
        self.dias: dict[date, r.LinhaDia] = {}
        self.gravados: list[tuple[date, r.DadosDia, str]] = []

    def obter(self, dia):
        return self.dias.get(dia)

    def guardar(self, dia, dados, obs):
        self.gravados.append((dia, dados, obs))
        calc = r.calcular_dia(dados)
        linha = r.LinhaDia(data=dia, tipo=dados.tipo, entrada=dados.entrada, saida=calc.saida,
                           trabalhado=calc.trabalhado, normais=calc.normais, extra=calc.extra)
        self.dias[dia] = linha
        return linha

    def apagar(self, dia):
        return self.dias.pop(dia, None) is not None


def _dialogo(folha, dia=date(2026, 10, 1), **kw):
    config = kw.pop("config", r.ConfigHoras(saida_habitual=19 * 60))
    return RegistoHorasDiaDialog(None, dia=dia, config=config, obter=folha.obter,
                                 guardar=kw.pop("guardar", folha.guardar), apagar=folha.apagar, **kw)


def test_dia_novo_vem_com_o_horario_habitual_e_mostra_as_contas() -> None:
    folha = _Folha()
    dialogo = _dialogo(folha)
    assert dialogo.tipo() == r.TIPO_UTIL
    assert dialogo.entrada_edit.time() == QTime(8, 0)
    assert dialogo.saida_edit.time() == QTime(19, 0)
    assert dialogo.almoco_check.isChecked()
    assert dialogo.resultado_label.text() == "8 + 2"
    assert "10h trabalhadas" in dialogo.detalhe_label.text()
    assert not dialogo.apagar_button.isVisible()


def test_feriado_e_fim_de_semana_vem_com_o_tipo_certo() -> None:
    folha = _Folha()
    assert _dialogo(folha, dia=date(2026, 10, 5)).tipo() == r.TIPO_FERIADO
    sabado = _dialogo(folha, dia=date(2026, 10, 3))
    assert sabado.tipo() == r.TIPO_FIM_SEMANA
    assert sabado.bloco_util.isHidden() and not sabado.bloco_horas.isHidden()


def test_guardar_e_seguinte_passa_ao_dia_a_seguir() -> None:
    folha = _Folha()
    dialogo = _dialogo(folha)
    dialogo.observacoes_edit.setText("Feira")
    dialogo.guardar_seguinte_button.click()
    assert folha.gravados[0][0] == date(2026, 10, 1)
    assert folha.gravados[0][2] == "Feira"
    assert dialogo.dia == date(2026, 10, 2) and dialogo.alterou
    assert dialogo.observacoes_edit.text() == ""


def test_segundo_periodo_e_folga() -> None:
    folha = _Folha()
    dialogo = _dialogo(folha)
    dialogo.saida_edit.setTime(QTime(17, 0))
    dialogo.segundo_check.setChecked(True)
    dialogo.entrada2_edit.setTime(QTime(20, 0))
    dialogo.saida2_edit.setTime(QTime(23, 0))
    assert dialogo.resultado_label.text() == "8 + 3"
    dados = dialogo.dados()
    assert (dados.entrada2, dados.saida2) == (1200, 1380)

    dialogo._radios[r.TIPO_FOLGA].setChecked(True)
    assert dialogo.horas_spin.value() == 8
    assert dialogo.resultado_label.text() == f"{r.MENOS}8"


def test_erro_fica_no_dialogo_e_nao_grava() -> None:
    folha = _Folha()
    dialogo = _dialogo(folha, dia=date(2026, 10, 3))  # sábado sem horas
    dialogo.guardar_button.click()
    assert folha.gravados == []
    assert "horas trabalhadas" in dialogo.erro_label.text()


def test_so_consulta_para_a_folha_de_outra_pessoa() -> None:
    folha = _Folha()
    folha.dias[date(2026, 10, 1)] = r.LinhaDia(data=date(2026, 10, 1), tipo=r.TIPO_UTIL,
                                              entrada=480, saida=1140, almoco=True)
    dialogo = _dialogo(folha, guardar=None, nome="Pedro")
    assert dialogo.guardar_button.isHidden() and dialogo.apagar_button.isHidden()
    assert not dialogo.observacoes_edit.isEnabled()
    assert "Pedro" in dialogo.windowTitle()


# ---- envio do mês --------------------------------------------------------------------
def test_dialogo_de_envio_mostra_resumo_e_dias_em_falta() -> None:
    dias = [r.LinhaDia(data=date(2026, 10, 1), tipo=r.TIPO_UTIL, entrada=480, saida=1140,
                       almoco=True, trabalhado=600, normais=480, extra=120)]
    dialogo = RegistoHorasEnvioDialog(None, nome="Paulo Catarino", ano=2026, mes=10, dias=dias,
                                      em_falta=[date(2026, 10, 2)], destinatario="f@x.pt",
                                      automatico=True)
    assert dialogo.tabela.rowCount() == 1
    assert dialogo.adiar_button.text() == "Lembrar amanhã"
    assert "Horas normais: 8h" in dialogo.mensagem_edit.toPlainText()
    dialogo.para_edit.setText("")
    dialogo.enviar_button.click()
    assert dialogo.acao is None  # sem destinatário não fecha
    dialogo.para_edit.setText("f@x.pt")
    dialogo.enviar_button.click()
    assert dialogo.acao == envio_mod.ACAO_ENVIAR


def test_corpo_html() -> None:
    assert corpo_html("Bom dia,\n\nLinha 1\nLinha <2>") == "<p>Bom dia,</p><p>Linha 1<br>Linha &lt;2&gt;</p>"


def test_enviar_mes_gera_pdf_envia_e_regista(base, monkeypatch, tmp_path) -> None:
    with base() as s:
        servico = RegistoHorasService(s)
        servico.guardar_config(2, r.ConfigHoras(pasta_pdf=str(tmp_path)))
        servico.guardar_dia(2, date(2026, 10, 1), r.DadosDia(tipo=r.TIPO_UTIL, entrada=480,
                                                             saida=1140, almoco=True))
    enviados = []
    monkeypatch.setattr(acoes, "enviar_email", lambda *a, **k: enviados.append((a, k)))
    monkeypatch.setattr(acoes, "carregar_email_config", lambda _s: EmailConfig(copia="orc@x.pt"))
    monkeypatch.setattr(acoes.RegistoHorasEnvioDialog, "exec", lambda self: setattr(self, "acao", envio_mod.ACAO_ENVIAR))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(acoes.diario_bordo, "registar_acao", lambda *a, **k: None)

    acao = acoes.enviar_mes(QWidget(), user_id=2, nome_conta="Paulo Catarino", email_conta="p@x.pt",
                            ano=2026, mes=10)

    assert acao == envio_mod.ACAO_ENVIAR
    (destino, assunto, _html, anexos), kwargs = enviados[0]
    assert destino == "financeiro@lancaencanto.pt"
    assert "outubro de 2026" in assunto
    assert anexos[0].endswith("HORAS_PAULO_CATARINO_OUTUBRO_2026.pdf")
    assert kwargs["config"].copia == ""  # a cópia dos orçamentos não recebe horas
    with base() as s:
        assert RegistoHorasService(s).ultimo_envio(2, 2026, 10).destinatario == destino


# ---- página ----------------------------------------------------------------------------
def test_pagina_mostra_o_mes_e_o_resumo(base) -> None:
    hoje = date.today()
    with base() as s:
        RegistoHorasService(s).guardar_dia(2, date(hoje.year, hoje.month, 1),
                                           r.DadosDia(tipo=r.TIPO_FOLGA, horas=480))
    pagina = pagina_mod.RegistoHorasPage(user_id=2, nome="Paulo Catarino")
    assert pagina.table.rowCount() == len(r.dias_do_mes(hoje.year, hoje.month))
    assert pagina.table.item(0, 4).text() == f"{r.MENOS}8"
    assert pagina._resumo_valores[-1].text() == f"{r.MENOS}8h"
    assert not pagina.colaborador_combo.isVisibleTo(pagina)
    assert pagina.status_label.objectName() == "registoHorasStatus"


def test_admin_escolhe_a_folha_e_so_consulta(base) -> None:
    with base() as s:
        RegistoHorasService(s).guardar_dia(2, date(2026, 10, 1),
                                           r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1140, almoco=True))
    pagina = pagina_mod.RegistoHorasPage(user_id=1, nome="Administrador Martelo", admin=True)
    nomes = [pagina.colaborador_combo.itemText(i) for i in range(pagina.colaborador_combo.count())]
    assert nomes == ["Paulo Catarino", "Pedro", "Administrador Martelo (a minha folha)"]
    assert pagina.so_leitura
    assert pagina.registar_hoje_button.isHidden() and pagina.enviar_button.isHidden()
    assert pagina.editar_button.text() == "Ver dia"
    pagina._ano, pagina._mes = 2026, 10
    pagina.carregar()
    assert pagina.table.item(0, 4).text() == "8 + 2"


def test_mostrar_dia_vai_ao_mes_certo(base, monkeypatch) -> None:
    pagina = pagina_mod.RegistoHorasPage(user_id=2, nome="Paulo Catarino")
    abertos = []
    monkeypatch.setattr(pagina, "_abrir_editor", abertos.append)
    pagina.mostrar_dia(date(2025, 4, 28), editar=True)
    assert (pagina._ano, pagina._mes) == (2025, 4)
    assert pagina.table.currentRow() == 27
    assert abertos == [date(2025, 4, 28)]


def test_mes_ja_enviado_pede_confirmacao_antes_de_alterar(base, monkeypatch) -> None:
    with base() as s:
        servico = RegistoHorasService(s)
        servico.registar_envio(2, 2026, 10, destinatario="f@x.pt", resumo=r.ResumoMes())
    pagina = pagina_mod.RegistoHorasPage(user_id=2, nome="Paulo Catarino")
    perguntas = []
    monkeypatch.setattr(QMessageBox, "question",
                        lambda *a, **k: perguntas.append(a[2]) or QMessageBox.StandardButton.No)
    dados = r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1140, almoco=True)
    assert pagina._guardar_dia(date(2026, 10, 1), dados, "") is None
    assert "já foram enviadas" in perguntas[0]
    with base() as s:
        assert RegistoHorasService(s).listar_mes(2, 2026, 10) == []


# ---- avisos ------------------------------------------------------------------------------
def test_lembrete_dos_dias_por_registar(base, monkeypatch) -> None:
    with base() as s:
        RegistoHorasService(s).guardar_dia(2, date(2026, 10, 1),
                                           r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1140, almoco=True))
    textos, abertos = [], []
    monkeypatch.setattr(QMessageBox, "exec", lambda self: textos.append(self.text()))
    aviso = avisos.AvisosRegistoHoras(QWidget(), user_id=2, ativo=True,
                                      abrir_dia=lambda d, e: abertos.append((d, e)))
    aviso._relogio.stop()
    aviso.verificar(datetime(2026, 10, 8, 9, 0))
    assert textos and "3 dias úteis" in textos[0]
    aviso.verificar(datetime(2026, 10, 8, 15, 0))
    assert len(textos) == 1  # uma vez por dia


def test_envio_do_dia_2(base, monkeypatch) -> None:
    with base() as s:
        RegistoHorasService(s).guardar_dia(2, date(2026, 10, 1),
                                           r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1140, almoco=True))
    pedidos = []
    monkeypatch.setattr(avisos.acoes, "enviar_mes",
                        lambda *a, **k: pedidos.append((k["ano"], k["mes"], k["automatico"])) or envio_mod.ACAO_ADIAR)
    monkeypatch.setattr(QMessageBox, "exec", lambda self: None)
    aviso = avisos.AvisosRegistoHoras(QWidget(), user_id=2, ativo=True)
    aviso._relogio.stop()
    aviso.verificar(datetime(2026, 11, 2, 9, 0))
    assert pedidos == []
    aviso.verificar(datetime(2026, 11, 2, 9, 25))
    assert pedidos == [(2026, 10, True)]
    aviso.verificar(datetime(2026, 11, 2, 11, 0))
    assert len(pedidos) == 1  # «Lembrar amanhã»
    aviso.verificar(datetime(2026, 11, 3, 9, 0))
    assert len(pedidos) == 2


def test_avisos_desligados_nas_definicoes(base, monkeypatch) -> None:
    with base() as s:
        RegistoHorasService(s).guardar_config(2, r.ConfigHoras(lembrete_diario=False, envio_mensal=False))
    monkeypatch.setattr(QMessageBox, "exec", lambda self: pytest.fail("não devia avisar"))
    monkeypatch.setattr(avisos.acoes, "enviar_mes", lambda *a, **k: pytest.fail("não devia enviar"))
    aviso = avisos.AvisosRegistoHoras(QWidget(), user_id=2, ativo=True)
    aviso._relogio.stop()
    aviso.verificar(datetime(2026, 11, 3, 10, 0))


def test_sem_menu_nao_ha_avisos() -> None:
    aviso = avisos.AvisosRegistoHoras(QWidget(), user_id=2, ativo=False)
    assert not aviso.ativo and not aviso._relogio.isActive()


# ---- menu e acessos -------------------------------------------------------------------------
def test_menu_nasce_desligado_e_tem_descricao() -> None:
    assert "menu.registo_horas" in MENU_PERMISSIONS
    assert DEFAULT_USER_PERMISSIONS["menu.registo_horas"] is False
    assert DEFAULT_USER_PERMISSIONS["menu.producao"] is True
    assert "contabilidade" in DESCRICOES_ACESSOS["menu.registo_horas"].o_que_faz


def test_janela_principal_liga_a_pagina_e_os_avisos() -> None:
    from app.ui.main_window import MainWindow

    fonte = inspect.getsource(MainWindow)
    assert '_criar_item("Registo de Horas", "registo_horas")' in fonte
    assert '"registo_horas": "menu.registo_horas"' in fonte
    assert "AvisosRegistoHoras(" in fonte
    assert "and not is_admin(self.authenticated_user)" in fonte
