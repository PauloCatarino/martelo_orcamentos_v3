"""Memorizar o login neste PC (pedido do Paulo, 24-09-2026).

O Martelo pedia utilizador e palavra-passe sempre que abria. Agora, com o visto
«Memorizar neste computador», entra sozinho; a palavra-passe fica no Gestor de
Credenciais do Windows. Os testes simulam o Windows: não tocam no Gestor real.
"""

from __future__ import annotations

import inspect
import os
import sys
import types
from contextlib import contextmanager
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QMessageBox

from app.core import login_memorizado
from app.db.session import BaseIndisponivel, CredenciaisInvalidas


class _GestorFalso:
    """Faz de Gestor de Credenciais do Windows, em memória."""

    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    def __init__(self) -> None:
        self.guardado: dict[str, dict] = {}

    def CredWrite(self, credencial, _flags):  # noqa: N802 - nome do pywin32
        blob = credencial["CredentialBlob"].encode("utf-16-le")
        self.guardado[credencial["TargetName"]] = {**credencial, "CredentialBlob": blob}

    def CredRead(self, alvo, _tipo):  # noqa: N802
        if alvo not in self.guardado:
            raise OSError(1168, "CredRead", "Elemento não encontrado.")
        return self.guardado[alvo]

    def CredDelete(self, alvo, _tipo, _flags):  # noqa: N802
        if alvo not in self.guardado:
            raise OSError(1168, "CredDelete", "Elemento não encontrado.")
        del self.guardado[alvo]


@pytest.fixture
def gestor(monkeypatch) -> _GestorFalso:
    falso = _GestorFalso()
    modulo = types.ModuleType("win32cred")
    for nome in ("CRED_TYPE_GENERIC", "CRED_PERSIST_LOCAL_MACHINE"):
        setattr(modulo, nome, getattr(falso, nome))
    for nome in ("CredWrite", "CredRead", "CredDelete"):
        setattr(modulo, nome, getattr(falso, nome))
    monkeypatch.setitem(sys.modules, "win32cred", modulo)
    return falso


# ----- guardar no Windows -----


def test_memoriza_le_e_esquece(gestor) -> None:
    assert login_memorizado.ler() is None

    assert login_memorizado.gravar("Pedro", "pãss€ 123")
    assert login_memorizado.ler() == ("Pedro", "pãss€ 123")
    assert login_memorizado.e_de("pedro")
    assert not login_memorizado.e_de("admin")

    login_memorizado.esquecer()
    assert login_memorizado.ler() is None
    login_memorizado.esquecer()  # já não havia: não rebenta


def test_fica_so_neste_pc_e_separado_por_base(gestor, monkeypatch) -> None:
    from app.config.settings import settings

    monkeypatch.setattr(settings, "DB_NAME", "martelo_v3")
    login_memorizado.gravar("paulo", "x")
    credencial = gestor.guardado["Martelo Orcamentos V3 (martelo_v3)"]
    assert credencial["Persist"] == gestor.CRED_PERSIST_LOCAL_MACHINE

    monkeypatch.setattr(settings, "DB_NAME", "martelo_v3_dev")
    assert login_memorizado.ler() is None


def test_windows_a_falhar_nunca_impede_o_arranque(monkeypatch) -> None:
    modulo = types.ModuleType("win32cred")

    def _rebenta(*_a, **_k):
        raise RuntimeError("sem acesso")

    modulo.CRED_TYPE_GENERIC = 1
    modulo.CRED_PERSIST_LOCAL_MACHINE = 2
    modulo.CredRead = modulo.CredWrite = modulo.CredDelete = _rebenta
    monkeypatch.setitem(sys.modules, "win32cred", modulo)

    assert login_memorizado.ler() is None
    assert login_memorizado.gravar("paulo", "x") is False
    login_memorizado.esquecer()


# ----- janela de login -----


@contextmanager
def _sessao_falsa():
    yield object()


def _perfil(username: str, role: str = "user"):
    return SimpleNamespace(username=username, nome=username, role=role)


@pytest.fixture
def janela_factory(gestor, monkeypatch):
    from app.ui import login_window as mod

    QApplication.instance() or QApplication([])
    ligacoes: list[tuple[str, str]] = []
    perfis = {"pedro": _perfil("Pedro"), "admin": _perfil("admin", "admin")}

    def _ligar(user, password):
        ligacoes.append((user, password))
        if password == "errada":
            raise CredenciaisInvalidas("x")
        if password == "sem-rede":
            raise BaseIndisponivel("A base não respondeu.")

    monkeypatch.setattr(mod, "ligar", _ligar)
    monkeypatch.setattr(mod, "SessionLocal", _sessao_falsa)
    monkeypatch.setattr(mod, "carregar_perfil", lambda _s, nome: perfis[nome.casefold()])
    monkeypatch.setattr(mod.diario_bordo, "registar_aviso", lambda *a: None)
    avisos: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "information", lambda _p, _t, texto, *a, **k: avisos.append(texto)
    )

    def _nova():
        janela = mod.LoginWindow()
        janela.ligacoes = ligacoes
        janela.avisos = avisos
        return janela

    return _nova


def test_sem_nada_memorizado_mostra_o_login(janela_factory) -> None:
    janela = janela_factory()

    assert janela.entrar_memorizado() is False
    assert janela.ligacoes == []
    assert janela.username_input.text() == ""
    assert not janela.memorizar_checkbox.isChecked()


def test_memorizado_entra_sozinho(janela_factory) -> None:
    login_memorizado.gravar("Pedro", "boa")
    janela = janela_factory()

    assert janela.entrar_memorizado() is True
    assert janela.ligacoes == [("Pedro", "boa")]
    assert janela.authenticated_user.username == "Pedro"


def test_password_mudada_esquece_e_explica(janela_factory) -> None:
    login_memorizado.gravar("Pedro", "errada")
    janela = janela_factory()

    assert janela.entrar_memorizado() is False
    assert login_memorizado.ler() is None
    assert "deixou de servir" in janela.error_label.text()
    # Fica tudo pronto para ele escrever a nova e voltar a memorizar.
    assert janela.username_input.text() == "Pedro"
    assert janela.memorizar_checkbox.isChecked()


def test_base_em_baixo_nao_apaga_a_memoria(janela_factory) -> None:
    login_memorizado.gravar("Pedro", "sem-rede")
    janela = janela_factory()

    assert janela.entrar_memorizado() is False
    assert login_memorizado.ler() == ("Pedro", "sem-rede")
    assert "não respondeu" in janela.error_label.text()


def test_admin_nunca_entra_sozinho(janela_factory) -> None:
    login_memorizado.gravar("admin", "boa")  # posto por fora do Martelo
    janela = janela_factory()

    assert janela.entrar_memorizado() is False
    assert janela.authenticated_user is None
    assert login_memorizado.ler() is None


def _entrar(janela, username: str, password: str) -> None:
    janela.username_input.setText(username)
    janela.password_input.setText(password)
    janela.handle_login()


def test_com_o_visto_fica_memorizado(janela_factory) -> None:
    janela = janela_factory()
    janela.memorizar_checkbox.setChecked(True)

    _entrar(janela, "Pedro", "boa")

    assert login_memorizado.ler() == ("Pedro", "boa")


def test_tirar_o_visto_esquece_o_proprio(janela_factory) -> None:
    login_memorizado.gravar("Pedro", "boa")
    janela = janela_factory()
    janela.memorizar_checkbox.setChecked(False)

    _entrar(janela, "Pedro", "boa")

    assert login_memorizado.ler() is None


def test_admin_no_pc_do_colega_nao_lhe_mexe_no_login(janela_factory) -> None:
    """O Paulo entra como admin no PC do Pedro (mudança de utilizador)."""
    login_memorizado.gravar("Pedro", "boa")
    janela = janela_factory()
    assert janela.username_input.text() == "Pedro"
    assert janela.memorizar_checkbox.isChecked()

    # Escrever outro nome tira o visto sozinho...
    janela.username_input.clear()
    janela.username_input.textEdited.emit("admin")
    assert not janela.memorizar_checkbox.isChecked()
    # ...e voltar ao nome memorizado repõe-no.
    janela.username_input.textEdited.emit("pedro")
    assert janela.memorizar_checkbox.isChecked()
    janela.username_input.textEdited.emit("admin")

    _entrar(janela, "admin", "boa")

    assert janela.result() == janela.DialogCode.Accepted
    assert login_memorizado.ler() == ("Pedro", "boa")


def test_admin_com_o_visto_entra_mas_nao_fica_memorizado(janela_factory) -> None:
    janela = janela_factory()
    janela.memorizar_checkbox.setChecked(True)

    _entrar(janela, "admin", "boa")

    assert janela.result() == janela.DialogCode.Accepted
    assert login_memorizado.ler() is None
    assert janela.avisos and "administrador" in janela.avisos[0]


# ----- arranque e mudança de palavra-passe -----


def test_so_entra_sozinho_ao_abrir_o_martelo() -> None:
    """Depois de uma mudança de utilizador a janela aparece sempre."""
    import app.main as main

    fonte = inspect.getsource(main.main)
    antes_do_ciclo, ciclo = fonte.split("while True:", 1)
    assert "entrar_sozinho = True" in antes_do_ciclo
    assert "entrar_sozinho and login_window.entrar_memorizado()" in ciclo
    assert ciclo.index("entrar_memorizado()") < ciclo.index("entrar_sozinho = False")
    assert "entrar_sozinho = True" not in ciclo


def test_mudar_a_password_atualiza_a_memorizada(gestor, monkeypatch) -> None:
    from PySide6.QtWidgets import QInputDialog

    from app.services import user_admin_service
    from app.ui import main_window as mod

    login_memorizado.gravar("Pedro", "antiga")
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("nova-123", True))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(user_admin_service, "mudar_a_minha_password", lambda *a: None)
    monkeypatch.setattr(mod, "SessionLocal", _sessao_falsa)

    mod.MainWindow.abrir_mudar_password(SimpleNamespace(authenticated_user=_perfil("Pedro")))

    assert login_memorizado.ler() == ("Pedro", "nova-123")


def test_mudar_a_password_de_outro_nao_mexe_na_memorizada(gestor, monkeypatch) -> None:
    from PySide6.QtWidgets import QInputDialog

    from app.services import user_admin_service
    from app.ui import main_window as mod

    login_memorizado.gravar("Pedro", "antiga")
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("nova-123", True))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(user_admin_service, "mudar_a_minha_password", lambda *a: None)
    monkeypatch.setattr(mod, "SessionLocal", _sessao_falsa)

    mod.MainWindow.abrir_mudar_password(SimpleNamespace(authenticated_user=_perfil("admin", "admin")))

    assert login_memorizado.ler() == ("Pedro", "antiga")
