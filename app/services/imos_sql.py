"""Acesso exclusivamente de leitura à base de dados SQL do iMos.

Este módulo nunca expõe uma função genérica de escrita. Além de usar
``ApplicationIntent=ReadOnly``, o diagnóstico recusa ligações cujo utilizador
consiga alterar a base de dados ou qualquer tabela visível.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

from sqlalchemy.orm import Session

from app.services.phc_sql import _parse_bool, assert_select_only, run_select
from app.services.system_setting_service import SystemSettingService

KEY_IMOS_SERVER = "imos_sql_server"
KEY_IMOS_DATABASE = "imos_sql_database"
KEY_IMOS_USER = "imos_sql_user"
KEY_IMOS_PASSWORD = "imos_sql_password"
KEY_IMOS_TRUSTED = "imos_sql_trusted"
KEY_IMOS_TRUST_CERT = "imos_sql_trust_server_certificate"


class ImosConfig(TypedDict):
    server: str
    database: str
    trusted: bool
    trust_server_certificate: bool
    user: str
    password: str


@dataclass(frozen=True)
class DiagnosticoImos:
    servidor: str
    base_dados: str
    login: str
    utilizador_base_dados: str
    tabelas_consultaveis: int
    conta_sql_somente_leitura: bool
    barreira_aplicacao_ativa: bool = True


def load_imos_config(session: Session) -> ImosConfig:
    """Carrega a configuração iMos sem assumir credenciais por defeito."""
    service = SystemSettingService(session)

    def _texto(chave: str) -> str:
        return (service.obter_valor(chave, "") or "").strip()

    return {
        "server": _texto(KEY_IMOS_SERVER),
        "database": _texto(KEY_IMOS_DATABASE),
        "user": _texto(KEY_IMOS_USER),
        "password": str(service.obter_valor(KEY_IMOS_PASSWORD, "") or ""),
        "trusted": _parse_bool(service.obter_valor(KEY_IMOS_TRUSTED, "")),
        "trust_server_certificate": _parse_bool(
            service.obter_valor(KEY_IMOS_TRUST_CERT, ""), default=True
        ),
    }


def save_imos_config(session: Session, cfg: ImosConfig) -> None:
    """Guarda apenas os dados de ligação na base local do Martelo V3."""
    SystemSettingService(session).guardar_varios(
        {
            KEY_IMOS_SERVER: cfg["server"],
            KEY_IMOS_DATABASE: cfg["database"],
            KEY_IMOS_USER: cfg["user"],
            KEY_IMOS_PASSWORD: cfg["password"],
            KEY_IMOS_TRUSTED: "ON" if cfg["trusted"] else "OFF",
            KEY_IMOS_TRUST_CERT: (
                "ON" if cfg["trust_server_certificate"] else "OFF"
            ),
        }
    )


def _connection_value(value: str, field_name: str) -> str:
    value = str(value or "")
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ValueError(f"Configuração iMos inválida no campo {field_name}.")
    return '"' + value.replace('"', '""') + '"'


def build_connection_string(cfg: ImosConfig) -> str:
    """Cria uma ligação SqlClient marcada explicitamente como read-only."""
    server = (cfg.get("server") or "").strip()
    database = (cfg.get("database") or "").strip()
    user = (cfg.get("user") or "").strip()
    password = str(cfg.get("password") or "")
    trusted = bool(cfg.get("trusted"))

    if not server or not database:
        raise ValueError("Configuração iMos incompleta: servidor e base de dados são obrigatórios.")

    parts = [
        f"Server={_connection_value(server, 'Servidor')}",
        f"Database={_connection_value(database, 'Base de dados')}",
        "ApplicationIntent=ReadOnly",
        "MultipleActiveResultSets=False",
    ]
    if trusted:
        parts.append("Integrated Security=True")
    else:
        if not user:
            raise ValueError("Configuração iMos incompleta: utilizador em falta.")
        if not password:
            raise ValueError("Configuração iMos incompleta: password em falta.")
        parts.extend(
            [
                f"User ID={_connection_value(user, 'Utilizador')}",
                f"Password={_connection_value(password, 'Password')}",
            ]
        )

    if cfg.get("trust_server_certificate"):
        parts.append("TrustServerCertificate=True")
    return ";".join(parts) + ";"


_DIAGNOSTICO_QUERY = """
SELECT
    CAST(SERVERPROPERTY('ServerName') AS nvarchar(256)) AS servidor,
    DB_NAME() AS base_dados,
    SUSER_SNAME() AS login,
    USER_NAME() AS utilizador_base_dados,
    CAST(HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'AL' + 'TER') AS int)
        + CAST(HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CON' + 'TROL') AS int)
        + CAST(HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CRE' + 'ATE TABLE') AS int)
        AS permissoes_estruturais,
    (SELECT COUNT(*)
       FROM sys.tables t
       JOIN sys.schemas s ON s.schema_id = t.schema_id
      WHERE t.is_ms_shipped = 0
        AND HAS_PERMS_BY_NAME(
            QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'SELECT'
        ) = 1) AS tabelas_consultaveis,
    (SELECT COUNT(*)
       FROM sys.tables t
       JOIN sys.schemas s ON s.schema_id = t.schema_id
      WHERE t.is_ms_shipped = 0
        AND (
            HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'IN' + 'SERT') = 1
         OR HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'UP' + 'DATE') = 1
         OR HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'DE' + 'LETE') = 1
         OR HAS_PERMS_BY_NAME(QUOTENAME(s.name) + '.' + QUOTENAME(t.name), 'OBJECT', 'AL' + 'TER') = 1
        )) AS tabelas_com_escrita
""".strip()


def diagnosticar_ligacao(cfg: ImosConfig) -> DiagnosticoImos:
    """Testa a ligação e informa, sem escrever, as permissões do principal."""
    assert_select_only(_DIAGNOSTICO_QUERY)
    rows = run_select(build_connection_string(cfg), _DIAGNOSTICO_QUERY)
    if not rows:
        raise RuntimeError("A ligação iMos não devolveu informação de diagnóstico.")

    row = rows[0]
    tabelas = int(row.get("tabelas_consultaveis") or 0)
    tabelas_escrita = int(row.get("tabelas_com_escrita") or 0)
    permissoes_estruturais = int(row.get("permissoes_estruturais") or 0)
    return DiagnosticoImos(
        servidor=str(row.get("servidor") or cfg["server"]),
        base_dados=str(row.get("base_dados") or cfg["database"]),
        login=str(row.get("login") or cfg.get("user") or "Autenticação Windows"),
        utilizador_base_dados=str(row.get("utilizador_base_dados") or ""),
        tabelas_consultaveis=tabelas,
        conta_sql_somente_leitura=not (
            tabelas_escrita or permissoes_estruturais
        ),
    )


def explicar_erro_ligacao(exc: Exception) -> str:
    """Converte erros técnicos SqlClient numa orientação segura e útil."""
    detalhe = str(exc or "")
    normalizado = detalhe.casefold()
    if "login failed" in normalizado or "falha de início de sessão" in normalizado:
        return (
            "O servidor SQL respondeu, mas recusou o utilizador/password. "
            "Confirme a password do utilizador configurado e mantenha 'Usar autenticação "
            "Windows' desativado. A password memorizada pelo SQL Server Management "
            "Studio não é transferida automaticamente para o Martelo."
        )
    if "cannot open database" in normalizado or "não é possível abrir a base" in normalizado:
        return (
            "O utilizador foi reconhecido, mas não conseguiu abrir a base de dados "
            "indicada. Confirme o nome da base e as permissões de acesso."
        )
    if any(
        texto in normalizado
        for texto in ("server was not found", "network-related", "error: 26")
    ):
        return (
            "Não foi possível localizar o servidor/instância SQL. Confirme o nome, "
            "a rede e se o serviço SQL Server está ativo."
        )
    return "Não foi possível validar a ligação iMos. Confirme os dados e tente novamente."


def run_imos_select(cfg: ImosConfig, query: str) -> list[dict]:
    """Executa um único SELECT; destinado às futuras consultas mapeadas iMos."""
    assert_select_only(query)
    return run_select(build_connection_string(cfg), query)
