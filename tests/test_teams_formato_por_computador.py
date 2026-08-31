"""O formato do link do Teams é uma preferência DESTE computador.

Estava em ``system_settings``, e isso trazia dois problemas ao mesmo tempo:

* era o MESMO valor para toda a gente — e o formato depende do Teams instalado
  em cada máquina, portanto um valor único não pode servir dois PCs
  diferentes (o Paulo apanhou isto: "o meu PC tem 'Teams de trabalho' e não
  sei se vai funcionar com msteams");
* as contas normais só LEEM essa tabela, de propósito (é lá que vivem as
  credenciais das ligações e o interruptor da escrita no iMos). Quem tentasse
  mudar levava com "Não foi possível gravar o formato do link" e ficava sem
  saída — foi o que aconteceu à Andreia a 31-08-2026.
"""

from __future__ import annotations

import inspect
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from app.services import teams_service

_app = QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _preferencia_limpa(monkeypatch):
    """Cada teste começa sem nada guardado, e não suja o PC de quem corre."""
    guardado: dict[str, object] = {}

    class _Falso:
        def __init__(self, *_a, **_k) -> None:
            pass

        def value(self, chave, default=None):
            return guardado.get(chave, default)

        def setValue(self, chave, valor) -> None:
            guardado[chave] = valor

    monkeypatch.setattr(teams_service, "QSettings", _Falso)
    yield guardado


def test_sem_nada_guardado_e_sem_base_usa_o_padrao() -> None:
    assert teams_service.formato_configurado() == teams_service.FORMATO_PADRAO


def test_guardar_e_ler_no_proprio_computador() -> None:
    teams_service.guardar_formato("aplicacao")

    assert teams_service.formato_configurado() == "aplicacao"


def test_guardar_nao_toca_na_base_de_dados() -> None:
    """É esta a razão de ser da mudança: gravar sem permissões de escrita."""
    fonte = inspect.getsource(teams_service.guardar_formato)

    assert "SystemSettingService" not in fonte
    assert "session" not in fonte
    assert "QSettings" in fonte


def test_valor_estragado_cai_no_padrao() -> None:
    teams_service.guardar_formato("isto_nao_existe")

    assert teams_service.formato_configurado() == teams_service.FORMATO_PADRAO


def test_o_valor_antigo_da_base_serve_de_ponto_de_partida() -> None:
    """Quem já tinha escolhido um formato não o perde na primeira abertura."""
    sessao_falsa = object()

    class _Definicoes:
        def __init__(self, _s) -> None:
            pass

        def obter_valor(self, _chave, _default=None):
            return "pessoal"

    original = teams_service.__dict__.get("SystemSettingService")
    import app.services.system_setting_service as modulo

    guardado_original = modulo.SystemSettingService
    modulo.SystemSettingService = _Definicoes
    try:
        assert teams_service.formato_configurado(sessao_falsa) == "pessoal"
    finally:
        modulo.SystemSettingService = guardado_original
        if original is not None:  # pragma: no cover - defensivo
            teams_service.SystemSettingService = original


def test_o_que_esta_guardado_aqui_ganha_ao_que_esta_na_base() -> None:
    teams_service.guardar_formato("aplicacao")

    class _Definicoes:
        def __init__(self, _s) -> None:
            pass

        def obter_valor(self, _chave, _default=None):
            return "trabalho"

    import app.services.system_setting_service as modulo

    guardado_original = modulo.SystemSettingService
    modulo.SystemSettingService = _Definicoes
    try:
        assert teams_service.formato_configurado(object()) == "aplicacao"
    finally:
        modulo.SystemSettingService = guardado_original


def test_cada_utilizador_do_pc_tem_a_sua(monkeypatch) -> None:
    monkeypatch.setattr(
        teams_service.app_session, "current_user", SimpleNamespace(username="andreia")
    )
    teams_service.guardar_formato("aplicacao")

    monkeypatch.setattr(
        teams_service.app_session, "current_user", SimpleNamespace(username="paulo")
    )
    assert teams_service.formato_configurado() == teams_service.FORMATO_PADRAO


def test_os_tres_formatos_geram_ligacoes_diferentes() -> None:
    ligacoes = {
        formato: teams_service.link_chat_teams(
            ["projetos@lancaencanto.pt"], "olá", formato=formato
        )
        for formato, _rotulo, _base in teams_service.FORMATOS_LINK
    }

    assert ligacoes["trabalho"].startswith("https://teams.microsoft.com/")
    assert ligacoes["pessoal"].startswith("https://teams.live.com/")
    assert ligacoes["aplicacao"].startswith("msteams:/")
    # Em todos, o destinatário e o texto vão no link.
    for ligacao in ligacoes.values():
        assert "users=projetos@lancaencanto.pt" in ligacao
        assert "&message=" in ligacao


def test_a_janela_da_equipa_grava_sem_a_base() -> None:
    from app.ui.dialogs.equipa_dialog import EquipaDialog

    fonte = inspect.getsource(EquipaDialog._gravar_formato)

    assert "teams_service.guardar_formato" in fonte
    assert "SessionLocal" not in fonte
    # E diz-lhe que ficou só naquele computador, para não haver enganos.
    assert "NESTE computador" in fonte
