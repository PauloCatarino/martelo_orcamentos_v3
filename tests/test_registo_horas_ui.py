"""Registo de Horas: editor do dia, página, envio do mês, avisos e menu."""

from __future__ import annotations

import inspect
from datetime import date, datetime

import pytest
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
        linha = r.LinhaDia(data=dia, tipo=dados.tipo, periodos=calc.periodos, horas=dados.horas,
                           trabalhado=calc.trabalhado, normais=calc.normais, extra=calc.extra,
                           falta=calc.falta, ausencia=calc.ausencia, almoco=dados.almoco)
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
    assert [linha.valores() for linha in dialogo.linhas] == [(480, 19 * 60)]
    assert dialogo.almoco_check.isChecked()
    assert dialogo.resultado_label.text() == "8 + 2"
    assert "10h trabalhadas" in dialogo.detalhe_label.text()
    assert not dialogo.apagar_button.isVisible()
    assert dialogo.linha_ausencia.isHidden()  # só no teletrabalho


def test_feriado_e_fim_de_semana_vem_com_o_tipo_certo() -> None:
    folha = _Folha()
    assert _dialogo(folha, dia=date(2026, 10, 5)).tipo() == r.TIPO_FERIADO
    sabado = _dialogo(folha, dia=date(2026, 10, 3))
    assert sabado.tipo() == r.TIPO_FIM_SEMANA
    # Uma linha vazia (não herda as 08:00–17:00), o «Só o total» e sem jantar/acerto.
    assert [linha.valores() for linha in sabado.linhas] == [(None, None)]
    assert not sabado.bloco_linhas.isHidden() and sabado.bloco_horas.isHidden()
    assert not sabado.so_total_check.isHidden() and not sabado.almoco_check.isChecked()
    assert sabado.jantar_check.isHidden() and sabado.linha_acerto.isHidden()
    sabado.linhas[0].definir(540, 780)
    assert sabado.resultado_label.text() == "4"
    sabado.so_total_check.setChecked(True)
    assert sabado.bloco_linhas.isHidden() and not sabado.bloco_horas.isHidden()


def test_dia_novo_abre_no_tipo_habitual_e_mudar_de_tipo_nao_herda_as_horas() -> None:
    folha = _Folha()
    dialogo = _dialogo(folha, dia=date(2026, 10, 20),
                       config=r.ConfigHoras(tipo_habitual=r.TIPO_TELETRABALHO))
    assert dialogo.tipo() == r.TIPO_TELETRABALHO
    assert not dialogo.linha_ausencia.isHidden()
    dialogo._radios[r.TIPO_FERIAS].setChecked(True)
    assert [linha.valores() for linha in dialogo.linhas] == [(None, None)]
    dialogo._radios[r.TIPO_UTIL].setChecked(True)
    assert [linha.valores() for linha in dialogo.linhas] == [(480, 1020)]


def test_guardar_e_seguinte_passa_ao_dia_a_seguir() -> None:
    folha = _Folha()
    dialogo = _dialogo(folha)
    dialogo.observacoes_edit.setText("Feira")
    dialogo.guardar_seguinte_button.click()
    assert folha.gravados[0][0] == date(2026, 10, 1)
    assert folha.gravados[0][2] == "Feira"
    assert dialogo.dia == date(2026, 10, 2) and dialogo.alterou
    assert dialogo.observacoes_edit.text() == ""


def test_mais_uma_linha_e_folga() -> None:
    """O caso do Pedro: 08:00–17:00 e mais uma linha em casa à noite."""
    folha = _Folha()
    dialogo = _dialogo(folha)
    dialogo.linhas[0].saida.definir(17 * 60)
    dialogo.mais_button.click()
    assert len(dialogo.linhas) == 2 and dialogo.linhas[1].valores() == (None, None)
    # As saídas rápidas e o ✕ só na última linha.
    assert dialogo.linhas[0].rapidas.isHidden() and not dialogo.linhas[1].rapidas.isHidden()
    assert dialogo.linhas[0].tirar_button.isHidden() and not dialogo.linhas[1].tirar_button.isHidden()
    dialogo.linhas[1].definir(20 * 60, 23 * 60)
    assert dialogo.resultado_label.text() == "8 + 3"
    assert dialogo.dados().periodos == ((480, 1020), (1200, 1380))
    dialogo.linhas[1].botoes_rapidos[-1].click()  # «22h»
    assert dialogo.linhas[1].saida.minutos() == 22 * 60
    dialogo.linhas[1].tirar_button.click()
    assert len(dialogo.linhas) == 1 and dialogo.resultado_label.text() == "8"

    dialogo._radios[r.TIPO_FOLGA].setChecked(True)
    assert dialogo.horas_spin.value() == 8
    assert dialogo.resultado_label.text() == f"{r.MENOS}8"
    assert dialogo.bloco_linhas.isHidden()


def test_teletrabalho_com_consulta_e_ausencia_justificada() -> None:
    folha = _Folha()
    dialogo = _dialogo(folha, dia=date(2026, 10, 20), config=r.ConfigHoras())
    dialogo._radios[r.TIPO_TELETRABALHO].setChecked(True)
    dialogo.linhas[0].saida.definir(600)
    dialogo.mais_button.click()
    dialogo.linhas[1].definir(780, 1020)
    # O intervalo 10:00–13:00 já é o almoço: desliga-se sozinho e a janela diz porquê.
    assert not dialogo.almoco_check.isChecked()
    assert "10:00 → 13:00" in dialogo.nota_almoco_label.text()
    dialogo.mais_button.click()
    dialogo.linhas[2].definir(1200, 1380)
    assert dialogo.resultado_label.text() == "6 + 3"
    assert "faltam 2h" in dialogo.detalhe_label.text()
    dialogo.ausencia_spin.setValue(2)
    assert dialogo.resultado_label.text() == "8 + 3"
    dialogo.guardar_button.click()
    _dia, dados, _obs = folha.gravados[-1]
    assert dados.ausencia == 120 and len(dados.periodos) == 3


def test_almoco_ligado_a_mao_avisa_que_desconta_duas_vezes() -> None:
    dialogo = _dialogo(_Folha(), config=r.ConfigHoras())
    dialogo.linhas[0].saida.definir(750)
    dialogo.mais_button.click()
    dialogo.linhas[1].definir(810, 1020)
    assert not dialogo.almoco_check.isChecked()
    dialogo.almoco_check.click()
    assert dialogo.almoco_check.isChecked()
    assert "duas vezes" in dialogo.nota_almoco_label.text()
    # Tirar a linha que fazia o intervalo não volta a mexer na escolha da pessoa.
    dialogo.linhas[1].tirar_button.click()
    assert dialogo.almoco_check.isChecked()


def test_linhas_sobrepostas_e_hora_invalida_nao_gravam() -> None:
    folha = _Folha()
    dialogo = _dialogo(folha)
    dialogo.mais_button.click()
    dialogo.linhas[1].definir(660, 1080)
    dialogo.guardar_button.click()
    assert folha.gravados == [] and "sobrepõem-se" in dialogo.erro_label.text()
    dialogo.linhas[1].saida.lineEdit().setText("25:00")
    assert "Hora inválida na linha 2" in dialogo.detalhe_label.text()
    dialogo.guardar_button.click()
    assert folha.gravados == []


def test_linhas_fora_de_ordem_ficam_pela_ordem_ao_guardar() -> None:
    folha = _Folha()
    dialogo = _dialogo(folha, config=r.ConfigHoras())
    dialogo.linhas[0].definir(780, 1020)
    dialogo.mais_button.click()
    dialogo.linhas[1].definir(480, 600)
    dialogo.guardar_seguinte_button.click()
    assert folha.gravados[0][1].periodos == ((480, 600), (780, 1020))
    dialogo._ir_para(date(2026, 10, 1))
    assert [linha.valores() for linha in dialogo.linhas] == [(480, 600), (780, 1020)]


def test_dia_antigo_so_com_o_total_abre_assim() -> None:
    folha = _Folha()
    folha.dias[date(2026, 10, 4)] = r.LinhaDia(data=date(2026, 10, 4), tipo=r.TIPO_FIM_SEMANA,
                                              horas=180, trabalhado=180, extra=180)
    dialogo = _dialogo(folha, dia=date(2026, 10, 4))
    assert dialogo.so_total_check.isChecked() and dialogo.horas_spin.value() == 3
    assert "só com o total" in dialogo.nota_dia_label.text()
    assert dialogo.resultado_label.text() == "3"


def test_campo_de_hora_pode_ficar_vazio() -> None:
    from app.ui.widgets.campo_hora import CampoHora, ler

    assert (ler("830"), ler("0830"), ler("17h"), ler("24:00"), ler(""), ler("abc")) == (
        510, 510, 1020, 0, None, None,
    )
    campo = CampoHora(sugestao=lambda: 13 * 60)
    assert campo.minutos() is None and not campo.invalido()
    campo.stepBy(1)  # vazio: a primeira seta põe a hora sugerida
    assert campo.minutos() == 13 * 60 and campo.text() == "13:00"
    campo.lineEdit().setText("99")
    assert campo.invalido()
    campo.clear()
    assert campo.minutos() is None


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


def test_pagina_mostra_o_subsidio_de_alimentacao(base) -> None:
    with base() as s:
        servico = RegistoHorasService(s)
        servico.guardar_dia(2, date(2026, 10, 3), r.DadosDia(tipo=r.TIPO_FIM_SEMANA, horas=270))
        servico.guardar_dia(2, date(2026, 10, 2),
                            r.DadosDia(tipo=r.TIPO_UTIL, entrada=480, saida=1260, almoco=True))
    pagina = pagina_mod.RegistoHorasPage(user_id=2, nome="Paulo Catarino")
    pagina._ano, pagina._mes = 2026, 10
    pagina.carregar()
    titulo = pagina.table.horizontalHeaderItem(pagina_mod.COL_SUBSIDIO)
    assert titulo.text() == "Subs. Alimentação"
    assert "1,25 €" in titulo.toolTip()
    assert pagina.table.item(2, pagina_mod.COL_SUBSIDIO).text() == "5,00 €"  # sábado, 4h30
    assert pagina.table.item(1, pagina_mod.COL_SUBSIDIO).text() == ""  # dia útil 8 + 4
    assert pagina.subsidio_label.text() == "5,00 €"


def test_pagina_mostra_o_teletrabalho_com_todas_as_linhas(base) -> None:
    with base() as s:
        RegistoHorasService(s).guardar_dia(
            2, date(2026, 10, 20),
            r.DadosDia(tipo=r.TIPO_TELETRABALHO, periodos=((480, 600), (780, 1020), (1200, 1380)),
                       almoco=False),
            observacoes="Consulta",
        )
    pagina = pagina_mod.RegistoHorasPage(user_id=2, nome="Paulo Catarino")
    pagina._ano, pagina._mes = 2026, 10
    pagina.carregar()
    linha = 19
    assert pagina.table.item(linha, 2).text() == "Teletrabalho"
    assert pagina.table.item(linha, pagina_mod.COL_HORARIO).text() == "8h – 10h · 13h – 17h · 20h – 23h"
    assert pagina.table.item(linha, 4).text() == "6 + 3"
    assert pagina.table.item(linha, pagina_mod.COL_EXTRA).text() == f"+3h · {r.MENOS}2h"
    assert "teletrabalho: 1" in pagina.contagens_label.text()
    # Resumo: as 3h extra e as 2h em falta cada uma no seu sítio.
    valores = dict(zip((rot for rot, _ in r.ResumoMes().linhas()), (l.text() for l in pagina._resumo_valores)))
    assert valores["Horas extra em dias úteis"] == "3h"
    assert valores["Descontos (dias com menos horas e folgas)"] == f"{r.MENOS}2h"
    assert valores["Total de horas extra"] == "1h"


def test_definicoes_tem_o_tipo_de_dia_habitual() -> None:
    from app.ui.dialogs.registo_horas_definicoes_dialog import RegistoHorasDefinicoesDialog

    dialogo = RegistoHorasDefinicoesDialog(
        None, config=r.ConfigHoras(), nome_conta="Paulo", email_contabilidade="f@x.pt",
        pode_mudar_email=False,
    )
    assert dialogo.tipo_combo.currentData() == r.TIPO_UTIL
    dialogo.tipo_combo.setCurrentIndex(dialogo.tipo_combo.findData(r.TIPO_TELETRABALHO))
    assert dialogo.config().tipo_habitual == r.TIPO_TELETRABALHO
    assert dialogo.tipo_combo.toolTip()
