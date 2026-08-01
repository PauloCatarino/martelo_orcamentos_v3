"""A janela tem de dizer a que base esta' ligada.

A beta e a de desenvolvimento tem os mesmos dados e o mesmo aspeto: sem isto
escrito no ecra, nao ha' como saber em qual se esta' a trabalhar.
"""

from __future__ import annotations

import pytest

from app.ui import main_window


@pytest.fixture()
def settings_falsas(monkeypatch):
    """Troca as settings que a janela le', sem tocar no .env real."""

    def _definir(ambiente: str, base: str):
        from app.config import settings as modulo

        monkeypatch.setattr(modulo.settings, "APP_ENV", ambiente, raising=False)
        monkeypatch.setattr(modulo.settings, "DB_NAME", base, raising=False)

    return _definir


def test_beta_diz_que_e_beta(settings_falsas) -> None:
    settings_falsas("beta", "martelo_v3_beta")

    assert main_window._ambiente_e_base() == "BETA · martelo_v3_beta"
    assert "BETA" in main_window._titulo_da_janela()
    assert "martelo_v3_beta" in main_window._titulo_da_janela()


def test_desenvolvimento_tambem_se_identifica(settings_falsas) -> None:
    settings_falsas("development", "martelo_v3_dev")

    assert main_window._ambiente_e_base() == "DEVELOPMENT · martelo_v3_dev"


def test_producao_nao_leva_etiqueta(settings_falsas) -> None:
    """No dia a dia dos colegas a janela fica limpa, como sempre esteve."""
    settings_falsas("production", "martelo_orcamentos_v3")

    assert main_window._ambiente_e_base() == ""
    assert main_window._titulo_da_janela() == "Martelo Orçamentos V3"


def test_sem_ambiente_definido_nao_inventa_etiqueta(settings_falsas) -> None:
    settings_falsas("", "seja_qual_for")

    assert main_window._ambiente_e_base() == ""


def test_a_base_aparece_sempre_que_ha_etiqueta(settings_falsas) -> None:
    """E' o nome da base que resolve a duvida, nao o nome do ambiente."""
    settings_falsas("teste", "outra_base_qualquer")

    assert "outra_base_qualquer" in main_window._ambiente_e_base()
