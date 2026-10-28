"""Caminhos do Sistema com uma conta de perfil normal: só leitura, e dito porquê.

28-10: o Paulo entrou como ``paulo`` (perfil MySQL normal, que só lê a
``system_settings``), mudou o interruptor do Escritório para ON e carregou em
Guardar. Leu «Nao foi possivel guardar» e, ao Atualizar, o valor voltou a OFF —
sem nada que dissesse que era a conta.
"""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from types import SimpleNamespace

import pymysql
import pytest
from sqlalchemy.exc import OperationalError

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QAbstractItemView, QApplication  # noqa: E402

from app.ui.pages import caminhos_sistema_page as modulo  # noqa: E402
from app.ui.pages.caminhos_sistema_page import CaminhosSistemaPage, erro_sem_permissao  # noqa: E402

INTERRUPTOR = SimpleNamespace(
    chave="streamlit_escrita_ativa",
    valor="OFF",
    descricao="Streamlit - Enviar para o Aprovisionamento ao gravar uma obra em Produção (ON/OFF)",
    tipo="opcao",
    grupo="Streamlit",
)


def _recusado(codigo: int = 1142) -> OperationalError:
    return OperationalError(
        "UPDATE system_settings SET valor=%s",
        {},
        pymysql.err.OperationalError(
            codigo, "UPDATE command denied to user 'paulo'@'%' for table 'system_settings'"
        ),
    )


@pytest.fixture(scope="module")
def _app():
    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture()
def pagina(_app, monkeypatch):
    """A página com uma base falsa; ``perfil`` diz que conta está ligada."""
    estado = {"geridas": False, "admin": False, "guardar": None}

    @contextmanager
    def sessao():
        yield object()

    class Servico:
        def __init__(self, _session) -> None:
            pass

        def listar_configuracoes(self):
            return [INTERRUPTOR]

        def guardar_varios(self, valores):
            if estado["guardar"] is not None:
                raise estado["guardar"]
            return []

    monkeypatch.setattr(modulo, "SessionLocal", sessao)
    monkeypatch.setattr(modulo, "SystemSettingService", Servico)
    monkeypatch.setattr(
        modulo.mysql_contas_service, "contas_geridas", lambda _s: estado["geridas"]
    )
    monkeypatch.setattr(
        modulo.mysql_contas_service, "sou_admin_na_base", lambda _s: estado["admin"]
    )
    avisos: list[str] = []
    monkeypatch.setattr(modulo.QMessageBox, "warning", lambda *a, **k: avisos.append(a[2]))
    monkeypatch.setattr(modulo.QMessageBox, "information", lambda *a, **k: None)

    def criar(*, geridas: bool, admin: bool):
        estado.update(geridas=geridas, admin=admin)
        return CaminhosSistemaPage(), estado, avisos

    return criar


@pytest.mark.parametrize(
    ("erro", "esperado"),
    [
        (_recusado(1142), True),
        (_recusado(1143), True),
        (_recusado(2003), False),  # servidor em baixo: não é falta de permissão
        (ValueError("chave is required"), False),
    ],
)
def test_erro_sem_permissao(erro, esperado) -> None:
    assert erro_sem_permissao(erro) is esperado


def test_perfil_normal_abre_so_de_leitura_e_diz_porque(pagina) -> None:
    pagina_, _estado, _avisos = pagina(geridas=True, admin=False)

    assert not pagina_.save_button.isEnabled()
    assert "admin" in pagina_.save_button.toolTip()
    assert pagina_.table.editTriggers() == QAbstractItemView.EditTrigger.NoEditTriggers
    assert "Só leitura" in pagina_.status_label.text()
    assert "administrador" in pagina_.status_label.text()


@pytest.mark.parametrize(("geridas", "admin"), [(True, True), (False, False)])
def test_admin_e_conta_antiga_continuam_a_editar(pagina, geridas, admin) -> None:
    pagina_, _estado, _avisos = pagina(geridas=geridas, admin=admin)

    assert pagina_.save_button.isEnabled()
    assert pagina_.table.editTriggers() != QAbstractItemView.EditTrigger.NoEditTriggers
    assert "Só leitura" not in pagina_.status_label.text()


def test_guardar_recusado_pela_base_explica_que_e_a_conta(pagina) -> None:
    # Se a página não souber o perfil e deixar tentar, a recusa diz o mesmo.
    pagina_, estado, avisos = pagina(geridas=False, admin=False)
    estado["guardar"] = _recusado(1142)

    pagina_.guardar_configuracoes()

    assert "administrador (admin)" in pagina_.status_label.text()
    assert avisos and "administrador (admin)" in avisos[0]


def test_outra_falha_continua_com_a_mensagem_de_sempre(pagina, monkeypatch) -> None:
    pagina_, estado, avisos = pagina(geridas=False, admin=False)
    estado["guardar"] = _recusado(2003)
    erros: list[str] = []
    monkeypatch.setattr(modulo.diario_bordo, "registar_erro", lambda *a, **k: erros.append(a[0]))

    pagina_.guardar_configuracoes()

    assert pagina_.status_label.text() == "Nao foi possivel guardar os caminhos do sistema."
    assert avisos == []
    assert erros == ["Caminhos do Sistema: não guardou"]
