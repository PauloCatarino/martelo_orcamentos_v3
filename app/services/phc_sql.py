"""PHC (SQL Server) read-only access through SELECT queries.

Execution uses PowerShell + System.Data.SqlClient to avoid native ODBC/pyodbc
dependencies. The PHC database must only ever be read from this module.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from typing import Any, TypedDict

from sqlalchemy.orm import Session

from app.services.system_setting_service import SystemSettingService

KEY_PHC_SERVER = "phc_sql_server"
KEY_PHC_DATABASE = "phc_sql_database"
KEY_PHC_USER = "phc_sql_user"
KEY_PHC_PASSWORD = "phc_sql_password"
KEY_PHC_TRUSTED = "phc_sql_trusted"
KEY_PHC_TRUST_CERT = "phc_sql_trust_server_certificate"

DEFAULT_PHC_SERVER = r"Server_le\phc"
DEFAULT_PHC_DATABASE = "lancaencanto"
DEFAULT_PHC_USER = "adriano.silva"
DEFAULT_PHC_TRUSTED = False
DEFAULT_PHC_TRUST_CERT = True

_BANNED_TOKENS = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "MERGE",
    "EXEC",
    "CREATE",
    "INTO",
)


class PHCConfig(TypedDict):
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


def load_phc_config(session: Session) -> PHCConfig:
    """Read PHC configuration from system settings, with V2 defaults."""
    settings_service = SystemSettingService(session)

    def _texto(chave: str, default: str = "") -> str:
        return (settings_service.obter_valor(chave, "") or "").strip() or default

    password = settings_service.obter_valor(KEY_PHC_PASSWORD, "") or ""
    return {
        "server": _texto(KEY_PHC_SERVER, DEFAULT_PHC_SERVER),
        "database": _texto(KEY_PHC_DATABASE, DEFAULT_PHC_DATABASE),
        "user": _texto(KEY_PHC_USER, DEFAULT_PHC_USER),
        "password": str(password),
        "trusted": _parse_bool(
            settings_service.obter_valor(KEY_PHC_TRUSTED, ""),
            default=DEFAULT_PHC_TRUSTED,
        ),
        "trust_server_certificate": _parse_bool(
            settings_service.obter_valor(KEY_PHC_TRUST_CERT, ""),
            default=DEFAULT_PHC_TRUST_CERT,
        ),
    }


def build_connection_string(cfg: PHCConfig) -> str:
    server = (cfg.get("server") or "").strip()
    database = (cfg.get("database") or "").strip()
    user = (cfg.get("user") or "").strip()
    password = cfg.get("password") or ""
    trusted = bool(cfg.get("trusted"))
    trust_cert = bool(cfg.get("trust_server_certificate"))

    if not server or not database:
        raise ValueError(
            "Configuracao PHC incompleta: Servidor e Base de Dados sao obrigatorios."
        )

    parts = [f"Server={server}", f"Database={database}"]
    if trusted:
        parts.append("Integrated Security=True")
    else:
        if not user:
            raise ValueError(
                "Configuracao PHC incompleta: Utilizador em falta (ou ative Trusted)."
            )
        if not str(password).strip():
            raise ValueError("Configuracao PHC incompleta: Password em falta.")
        parts.append(f"User ID={user}")
        parts.append(f"Password={password}")

    if trust_cert:
        parts.append("TrustServerCertificate=True")

    return ";".join(parts) + ";"


def assert_select_only(query: str) -> None:
    """Ensure the query is a single SELECT statement."""
    q = (query or "").strip()
    if not q.upper().startswith("SELECT"):
        raise RuntimeError("Query invalida: apenas SELECT e permitido.")

    q_no_trailing = q.rstrip(";").strip()
    if ";" in q_no_trailing:
        raise RuntimeError("Query invalida: multiplos statements nao sao permitidos.")

    for token in _BANNED_TOKENS:
        if re.search(
            rf"\b{re.escape(token)}\b",
            q_no_trailing,
            flags=re.IGNORECASE,
        ):
            raise RuntimeError("Query invalida: apenas SELECT e permitido.")


def run_select(conn_str: str, query: str) -> list[dict[str, Any]]:
    """Run one read-only SELECT via PowerShell + System.Data.SqlClient."""
    assert_select_only(query)
    payload = {"conn": conn_str, "query": query}
    payload_b64 = base64.b64encode(
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    ps_script = r"""
param(
  [Parameter(Mandatory=$true)][string]$PayloadB64
)
$ErrorActionPreference = 'Stop'

$payloadJson = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PayloadB64))
$p = $payloadJson | ConvertFrom-Json
$connStr = [string]$p.conn
$query = [string]$p.query

if (-not $query.TrimStart().ToUpper().StartsWith('SELECT')) {
  throw 'Query invalida: apenas SELECT e permitido.'
}
$q2 = $query.Trim()
$q2 = $q2.TrimEnd(';').Trim()
if ($q2.Contains(';')) { throw 'Query invalida: multiplos statements nao sao permitidos.' }
$banned = @('INSERT','UPDATE','DELETE','DROP','ALTER','TRUNCATE','MERGE','EXEC','CREATE','INTO')
foreach ($t in $banned) {
  if ([regex]::IsMatch($q2, ('\b' + [regex]::Escape($t) + '\b'), [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
    throw 'Query invalida: apenas SELECT e permitido.'
  }
}

Add-Type -AssemblyName System.Data
$conn = New-Object System.Data.SqlClient.SqlConnection $connStr
$conn.Open()
try {
  $cmd = $conn.CreateCommand()
  $cmd.CommandText = $query
  $cmd.CommandTimeout = 30

  $dt = New-Object System.Data.DataTable
  $da = New-Object System.Data.SqlClient.SqlDataAdapter $cmd
  [void]$da.Fill($dt)

  $rows = @()
  foreach ($r in $dt.Rows) {
    $obj = [ordered]@{}
    foreach ($c in $dt.Columns) {
      $val = $r[$c.ColumnName]
      if ($val -is [System.DBNull]) { $val = $null }
      $obj[$c.ColumnName] = $val
    }
    $rows += [pscustomobject]$obj
  }
  $json = ConvertTo-Json -InputObject $rows -Depth 6 -Compress
  [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
} finally {
  $conn.Close()
}
"""

    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".ps1", delete=False
        ) as tf:
            tf.write(ps_script)
            temp_path = tf.name

        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            temp_path,
            payload_b64,
        ]
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        )
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            detail = "\n".join(s for s in (stderr, stdout) if s)
            raise RuntimeError(detail or f"Codigo de saida: {result.returncode}")

        raw_b64 = (result.stdout or "").strip()
        if not raw_b64:
            return []

        decoded = base64.b64decode(raw_b64).decode("utf-8", errors="replace")
        data = json.loads(decoded)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data

        return []
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def query_phc_clients(session: Session) -> list[dict[str, Any]]:
    """Read PHC clients from dbo.CL; upsert happens in a later phase."""
    query = (
        "SELECT NOME AS Nome, NOME2 AS Simplex, MORADA AS Morada, EMAIL AS Email, "
        "URL AS WEB, TLMVL AS Telemovel, TELEFONE AS Telefone, NO AS Num_PHC, "
        "OBS AS Info_1 FROM dbo.CL WITH (NOLOCK) ORDER BY NOME"
    )
    cfg = load_phc_config(session)
    return run_select(build_connection_string(cfg), query)


def contar_clientes_phc(session: Session) -> int:
    """Count records in dbo.CL; used by the PHC connection test button."""
    cfg = load_phc_config(session)
    rows = run_select(
        build_connection_string(cfg),
        "SELECT COUNT(*) AS total FROM dbo.CL WITH (NOLOCK)",
    )
    if not rows:
        return 0

    total = rows[0].get("total")
    return int(total) if total is not None else 0
