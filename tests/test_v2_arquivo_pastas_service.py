"""Tests for the read-only V2 budget-folder resolver."""

from __future__ import annotations

from datetime import date

from app.services.v2_arquivo_pastas_service import (
    _nomes_versao,
    ano_do_orcamento_v2,
    resolver_pasta_orcamento_v2,
)
from app.services.v2_arquivo_service import OrcamentoV2Resumo


def _item(*, numero="260775", versao="01", data=date(2026, 7, 15)):
    return OrcamentoV2Resumo(
        numero=numero,
        versao=versao,
        cliente="Cliente Teste",
        ref_cliente="",
        obra="",
        descricao="",
        estado="Enviado",
        data=data,
        total=None,
        utilizador="",
        tabela_origem="orcamentos",
    )


def test_ano_v2_usa_data_e_fallback_do_numero():
    assert ano_do_orcamento_v2(_item()) == 2026
    assert ano_do_orcamento_v2(_item(data="", numero="250001")) == 2025


def test_nomes_versao_priorizam_formato_v2_de_dois_digitos():
    assert _nomes_versao("1") == ("01", "1")
    assert _nomes_versao("01") == ("01",)


def test_resolver_reutiliza_pasta_existente_com_simplex_alterado(monkeypatch, tmp_path):
    import app.services.v2_arquivo_pastas_service as service

    pasta = tmp_path / "2026" / "260775_SIMPLEX_ANTIGO" / "01"
    pasta.mkdir(parents=True)

    class _Settings:
        def __init__(self, _session):
            pass

        def obter_valor(self, _key):
            return str(tmp_path)

    monkeypatch.setattr(service, "SystemSettingService", _Settings)

    assert resolver_pasta_orcamento_v2(object(), _item()) == pasta
