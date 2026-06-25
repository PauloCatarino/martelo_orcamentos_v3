"""STREAMLIT (SQL Server) - acesso READ-ONLY via SELECT.

Portado do Martelo V2 (``streamlit_sql.py``), adaptado ao V3: le a configuracao
das ``system_settings`` (grupo "Streamlit") e reutiliza o mecanismo PowerShell de
``phc_sql`` (``run_select``/``assert_select_only``). NUNCA escreve na BD externa.
"""

from __future__ import annotations

from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.services.phc_sql import assert_select_only, run_select
from app.services.system_setting_service import SystemSettingService

KEY_STREAMLIT_SERVER = "streamlit_sql_server"
KEY_STREAMLIT_DATABASE = "streamlit_sql_database"
KEY_STREAMLIT_USER = "streamlit_sql_user"
KEY_STREAMLIT_PASSWORD = "streamlit_sql_password"
KEY_STREAMLIT_TRUSTED = "streamlit_sql_trusted"
KEY_STREAMLIT_TRUST_CERT = "streamlit_sql_trust_server_certificate"

DEFAULT_STREAMLIT_SERVER = r"DESKTOP-PTJ4TE6,1433"
DEFAULT_STREAMLIT_DATABASE = "Lanca_Encanto2026"
DEFAULT_STREAMLIT_USER = "Lanca_Encanto_ReadOnly"
DEFAULT_STREAMLIT_PASSWORD = "Lanca_ReadOnly_2026!"
DEFAULT_STREAMLIT_TRUSTED = False
DEFAULT_STREAMLIT_TRUST_CERT = True


class StreamlitConfig(TypedDict):
    server: str
    database: str
    trusted: bool
    trust_server_certificate: bool
    user: str
    password: str


def _parse_bool(raw: Any, *, default: bool = False) -> bool:
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw

    texto = str(raw).strip()
    if not texto:
        return default

    return texto.lower() in {"1", "true", "yes", "y", "sim", "on"}


def load_streamlit_config(session: Session) -> StreamlitConfig:
    """Read Streamlit configuration from system settings, with V2 defaults."""
    settings_service = SystemSettingService(session)

    def _texto(chave: str, default: str = "") -> str:
        return (settings_service.obter_valor(chave, "") or "").strip() or default

    password = (
        settings_service.obter_valor(KEY_STREAMLIT_PASSWORD, "") or ""
    ).strip() or DEFAULT_STREAMLIT_PASSWORD
    return {
        "server": _texto(KEY_STREAMLIT_SERVER, DEFAULT_STREAMLIT_SERVER),
        "database": _texto(KEY_STREAMLIT_DATABASE, DEFAULT_STREAMLIT_DATABASE),
        "user": _texto(KEY_STREAMLIT_USER, DEFAULT_STREAMLIT_USER),
        "password": str(password),
        "trusted": _parse_bool(
            settings_service.obter_valor(KEY_STREAMLIT_TRUSTED, ""),
            default=DEFAULT_STREAMLIT_TRUSTED,
        ),
        "trust_server_certificate": _parse_bool(
            settings_service.obter_valor(KEY_STREAMLIT_TRUST_CERT, ""),
            default=DEFAULT_STREAMLIT_TRUST_CERT,
        ),
    }


def build_connection_string(cfg: StreamlitConfig) -> str:
    server = (cfg.get("server") or "").strip()
    database = (cfg.get("database") or "").strip()
    user = (cfg.get("user") or "").strip()
    password = cfg.get("password") or ""
    trusted = bool(cfg.get("trusted"))
    trust_cert = bool(cfg.get("trust_server_certificate"))

    if not server or not database:
        raise ValueError(
            "Configuracao Streamlit incompleta: Servidor e Base de Dados sao obrigatorios."
        )

    parts = [
        f"Server={server}",
        f"Database={database}",
        "Encrypt=False",
        "Connection Timeout=60",
    ]
    if trusted:
        parts.append("Integrated Security=True")
    else:
        if not user:
            raise ValueError(
                "Configuracao Streamlit incompleta: Utilizador em falta (ou ative Trusted)."
            )
        if not str(password).strip():
            raise ValueError("Configuracao Streamlit incompleta: Password em falta.")
        parts.append(f"User ID={user}")
        parts.append(f"Password={password}")

    if trust_cert:
        parts.append("TrustServerCertificate=True")

    return ";".join(parts) + ";"


def query_encomendas_cliente_final(
    session: Session,
    *,
    ano_minimo: int,
    max_linhas: int = 0,
) -> list[dict]:
    """Le as encomendas Cliente Final (dbo.Encomendas) do Streamlit. SO-LEITURA.

    ``ano_minimo`` filtra por ``Ano >= <ano>``; ``max_linhas`` > 0 limita com TOP.
    As datas vem ja em "dd-mm-aaaa" do ``CONVERT(..., 104)``.
    """
    ano = int(ano_minimo)
    top = ""
    if max_linhas and int(max_linhas) > 0:
        top = f"TOP ({int(max_linhas)}) "

    query = (
        f"SELECT {top}"
        "Id, Numero, Ano, Cliente, Contacto, RefCliente, "
        "CONVERT(VARCHAR(10), DataRecepcao, 104) AS DataRecepcao, Responsavel, "
        "CONVERT(VARCHAR(10), DataEntrega, 104) AS DataEntrega, "
        "PrazoObrigatorio, Status, NumPaletes, TipoPaletes, "
        "FormatoPalete, ExisteMontagem, Anulada, Observacoes, Cliente_Abre "
        "FROM dbo.Encomendas WITH (NOLOCK) "
        f"WHERE Ano >= {ano} "
        "ORDER BY Ano DESC, Id DESC"
    )

    assert_select_only(query)
    conn_str = build_connection_string(load_streamlit_config(session))
    return run_select(conn_str, query)


def query_itens_encomenda(
    session: Session,
    *,
    encomenda_id: int,
    max_itens: int = 0,
) -> list[dict]:
    """Le os itens (dbo.ItensEncomenda) de uma encomenda do Streamlit. SO-LEITURA."""
    enc_id = int(encomenda_id)
    top = ""
    if max_itens and int(max_itens) > 0:
        top = f"TOP ({int(max_itens)}) "

    query = (
        f"SELECT {top}"
        "EncomendaId, RefObra, Referencia, Designacao, X, Y, Z, "
        "Quantidade, Unidade, Venda, ValorVenda, "
        "UnidadeAlternativa, QuantidadeAlternativa, Id "
        "FROM dbo.ItensEncomenda WITH (NOLOCK) "
        f"WHERE EncomendaId = {enc_id} "
        "ORDER BY Id ASC"
    )

    assert_select_only(query)
    conn_str = build_connection_string(load_streamlit_config(session))
    return run_select(conn_str, query)
