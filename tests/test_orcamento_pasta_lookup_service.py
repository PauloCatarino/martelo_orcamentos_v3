"""Tests for the read-only budget folder lookup used by the production page."""

from __future__ import annotations

import pytest

from app.services.orcamento_pasta_lookup_service import resolver_pasta_orcamento
from app.services.system_setting_service import SystemSettingService


@pytest.fixture()
def base_orcamentos(session, tmp_path):
    """Create ``base/2026/260661_FMOC/01`` and register the base folder."""
    pasta = tmp_path / "2026" / "260661_FMOC" / "01"
    pasta.mkdir(parents=True)
    SystemSettingService(session).guardar_valor("pasta_base_orcamentos", str(tmp_path))
    return tmp_path


def test_resolve_pasta_da_versao(session, base_orcamentos) -> None:
    pasta = resolver_pasta_orcamento(
        session, ano="2026", num_orcamento="260661", versao_orc="01"
    )

    assert pasta == base_orcamentos / "2026" / "260661_FMOC" / "01"


def test_versao_numerica_e_normalizada_para_dois_digitos(session, base_orcamentos) -> None:
    pasta = resolver_pasta_orcamento(
        session, ano="2026", num_orcamento="260661", versao_orc="1"
    )

    assert pasta == base_orcamentos / "2026" / "260661_FMOC" / "01"


def test_sem_versao_devolve_a_pasta_do_orcamento(session, base_orcamentos) -> None:
    pasta = resolver_pasta_orcamento(session, ano="2026", num_orcamento="260661")

    assert pasta == base_orcamentos / "2026" / "260661_FMOC"


def test_versao_inexistente_cai_na_pasta_do_orcamento(session, base_orcamentos) -> None:
    pasta = resolver_pasta_orcamento(
        session, ano="2026", num_orcamento="260661", versao_orc="09"
    )

    assert pasta == base_orcamentos / "2026" / "260661_FMOC"


def test_sem_numero_ou_ano_devolve_none(session, base_orcamentos) -> None:
    assert resolver_pasta_orcamento(session, ano="2026", num_orcamento="") is None
    assert resolver_pasta_orcamento(session, ano="", num_orcamento="260661") is None


def test_orcamento_desconhecido_devolve_none(session, base_orcamentos) -> None:
    assert (
        resolver_pasta_orcamento(session, ano="2026", num_orcamento="999999") is None
    )


def test_sem_pasta_base_configurada_devolve_none(session) -> None:
    assert (
        resolver_pasta_orcamento(session, ano="2026", num_orcamento="260661") is None
    )
