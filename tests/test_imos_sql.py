"""Testes da barreira de leitura da futura integração SQL iMos."""

from __future__ import annotations

import pytest

from app.services import imos_sql
from app.services.imos_sql import ImosConfig


def _cfg(**overrides) -> ImosConfig:
    cfg: ImosConfig = {
        "server": r"SERVIDOR\IMOS",
        "database": "imosdb",
        "user": "martelo_readonly",
        "password": "segredo;com;ponto",
        "trusted": False,
        "trust_server_certificate": True,
    }
    cfg.update(overrides)  # type: ignore[typeddict-item]
    return cfg


def test_connection_string_forca_application_intent_read_only() -> None:
    conn = imos_sql.build_connection_string(_cfg())

    assert "ApplicationIntent=ReadOnly" in conn
    assert "MultipleActiveResultSets=False" in conn
    assert 'Password="segredo;com;ponto"' in conn
    assert "TrustServerCertificate=True" in conn


def test_connection_string_exige_credenciais_sql() -> None:
    with pytest.raises(ValueError, match="utilizador"):
        imos_sql.build_connection_string(_cfg(user=""))
    with pytest.raises(ValueError, match="password"):
        imos_sql.build_connection_string(_cfg(password=""))


def test_connection_string_windows_nao_inclui_password() -> None:
    conn = imos_sql.build_connection_string(_cfg(trusted=True, user="", password=""))

    assert "Integrated Security=True" in conn
    assert "User ID=" not in conn
    assert "Password=" not in conn


def test_diagnostico_aceita_principal_apenas_de_leitura(monkeypatch) -> None:
    monkeypatch.setattr(
        imos_sql,
        "run_select",
        lambda _conn, _query: [
            {
                "servidor": "SQL01",
                "base_dados": "imosdb",
                "login": "martelo_readonly",
                "utilizador_base_dados": "martelo_readonly",
                "permissoes_estruturais": 0,
                "tabelas_consultaveis": 42,
                "tabelas_com_escrita": 0,
            }
        ],
    )

    result = imos_sql.diagnosticar_ligacao(_cfg())

    assert result.conta_sql_somente_leitura is True
    assert result.barreira_aplicacao_ativa is True
    assert result.tabelas_consultaveis == 42


@pytest.mark.parametrize(
    ("estruturais", "tabelas_escrita"), [(1, 0), (0, 1), (2, 7)]
)
def test_diagnostico_assinala_permissao_de_escrita_sem_executar_escrita(
    monkeypatch, estruturais: int, tabelas_escrita: int
) -> None:
    monkeypatch.setattr(
        imos_sql,
        "run_select",
        lambda _conn, _query: [
            {
                "permissoes_estruturais": estruturais,
                "tabelas_consultaveis": 10,
                "tabelas_com_escrita": tabelas_escrita,
            }
        ],
    )

    result = imos_sql.diagnosticar_ligacao(_cfg())
    assert result.conta_sql_somente_leitura is False


def test_diagnostico_aceita_ligacao_sem_tabelas_visiveis(monkeypatch) -> None:
    monkeypatch.setattr(
        imos_sql,
        "run_select",
        lambda _conn, _query: [
            {
                "permissoes_estruturais": 0,
                "tabelas_consultaveis": 0,
                "tabelas_com_escrita": 0,
            }
        ],
    )

    result = imos_sql.diagnosticar_ligacao(_cfg())
    assert result.tabelas_consultaveis == 0


def test_explicar_erro_login_remove_detalhe_tecnico() -> None:
    texto = imos_sql.explicar_erro_ligacao(
        RuntimeError("tmp123.ps1: Login failed for user 'IMOSADMIN'.")
    )
    assert "servidor SQL respondeu" in texto
    assert "password" in texto
    assert "tmp123" not in texto


def test_run_imos_select_bloqueia_escrita_antes_da_ligacao(monkeypatch) -> None:
    chamado = False

    def _run(*_args):
        nonlocal chamado
        chamado = True
        return []

    monkeypatch.setattr(imos_sql, "run_select", _run)
    with pytest.raises(RuntimeError):
        imos_sql.run_imos_select(_cfg(), "UPDATE artigo SET nome='x'")
    assert chamado is False
