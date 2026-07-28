"""Único canal de escrita do Martelo na base SQL do iMos.

Este módulo é deliberadamente separado de :mod:`app.services.imos_sql`, que
continua exclusivamente de leitura. Aqui a escrita é possível, mas fechada em
três barreiras:

1. Um interruptor explícito (``imos_escrita_ativa``, por defeito desligado).
2. Só existe uma operação: criar nós na árvore de encomendas. Não há nenhum
   caminho de código que produza ``UPDATE``, ``DELETE`` ou ``DROP``, nem que
   toque numa tabela que não seja ``dbo.IMORDFOLDER`` ou ``dbo.PROADMIN``.
3. Todos os valores viajam como ``SqlParameter`` tipados com o comprimento
   real da coluna; nada é interpolado no texto da query.

Cada nó criado gera duas linhas ligadas entre si: a linha da árvore em
``IMORDFOLDER`` (que recebe o ``DIR_ID`` do ``IDENTITY``) e a linha de dados em
``PROADMIN``, cujo ``PRODUCTIONID`` tem de ser esse mesmo ``DIR_ID``. As duas
inserções correm na mesma transação: ou ficam ambas, ou não fica nenhuma.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.services.imos_sql import (
    IMOS_TIPO_ENCOMENDA,
    IMOS_TIPO_PASTA,
    ImosConfig,
    _connection_value,
    nome_imos_valido,
)
from app.services.system_setting_service import SystemSettingService

KEY_IMOS_ESCRITA_ATIVA = "imos_escrita_ativa"

TIPOS_PERMITIDOS = (IMOS_TIPO_PASTA, IMOS_TIPO_ENCOMENDA)

# Colunas de dbo.PROADMIN que o Martelo pode preencher, com o tipo e o
# comprimento exatos do DDL do iMos. As colunas de fora desta lista ficam com o
# DEFAULT da própria tabela ('' ou 0) — nenhuma aceita NULL.
#
# Ausentes de propósito: ID e PRODUCTIONID (geridos pelo motor), NAME e TYPE
# (vêm do nó) e DATECREATE/LCHANGE (recebem GETDATE() no próprio INSERT).
COLUNAS_PROADMIN: dict[str, tuple[str, int]] = {
    "COMM": ("nvarchar", 80),
    "ARTICLENO": ("nvarchar", 30),
    "EMPLOYEE": ("nvarchar", 30),
    "CUSTOMER": ("nvarchar", 80),
    "CLIENT": ("nvarchar", 80),
    "PROGRAM": ("nvarchar", 80),
    "CONTYPE": ("nvarchar", 30),
    "DESIGN": ("nvarchar", 30),
    **{f"COLOUR{n}": ("nvarchar", 80) for n in range(1, 6)},
    **{f"INFO{n}": ("nvarchar", 80) for n in range(1, 11)},
    "EDITOR": ("nvarchar", 30),
    "LINE_NO": ("nvarchar", 16),
    "CNT": ("int", 0),
    "DESCRIPTION": ("nvarchar", 255),
    "DELIVERY_DATE": ("nvarchar", 150),
    **{f"LEVEL_{n}": ("nvarchar", 50) for n in range(1, 11)},
    "PICTURE_1": ("nvarchar", 255),
    "TEXT_SHORT": ("nvarchar", 255),
    "TEXT_LONG": ("nvarchar", 255),
    "STATUS": ("int", 0),
    "STARTDATE": ("nvarchar", 150),
    "ENDDATE": ("nvarchar", 150),
    "EXPENSE": ("nvarchar", 150),
    "RESPONSE": ("nvarchar", 150),
    "REFSTAT": ("int", 0),
    "SOURCE": ("nvarchar", 80),
    "ORDERLOCK": ("int", 0),
    "SHIPPING_DATE": ("nvarchar", 150),
    "EXPORTED": ("int", 0),
    "CMS_PROCESS": ("int", 0),
    "CMS_CALCULATION": ("int", 0),
    "CMS_PRICE": ("real", 0),
    "CMS_PRODUCTION": ("int", 0),
    "ORDERSTATUS": ("nvarchar", 30),
    "GLOBAL_SPEC": ("nvarchar", 30),
    "GLOBAL_SPEC_VERSION": ("nvarchar", 34),
    "DETAIL_SPEC": ("nvarchar", 30),
    "DETAIL_SPEC_VERSION": ("nvarchar", 34),
}

# Colunas que o chamador nunca pode indicar: são do motor ou do nó.
COLUNAS_RESERVADAS = frozenset(
    {"ID", "PRODUCTIONID", "NAME", "TYPE", "DATECREATE", "LCHANGE"}
)


@dataclass(frozen=True)
class NoParaCriar:
    """Um nó a criar: pasta/projeto ou encomenda.

    O pai indica-se de uma de duas formas, nunca as duas: ``parent_dir_id``
    para uma pasta que já existe no iMos, ou ``parent_indice`` para uma pasta
    criada mais acima na mesma lista (e portanto na mesma transação).
    """

    nome: str
    tipo: int
    parent_dir_id: int | None = None
    parent_indice: int | None = None
    campos: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NoCriado:
    """Resultado de um nó efetivamente criado no iMos."""

    nome: str
    tipo: int
    dir_id: int
    proadmin_id: int
    parent_dir_id: int


def carregar_escrita_ativa(session: Session) -> bool:
    """Indica se o interruptor de escrita no iMos está ligado (default: não)."""
    valor = (
        SystemSettingService(session).obter_valor(KEY_IMOS_ESCRITA_ATIVA, "") or ""
    ).strip()
    return valor.lower() in {"1", "true", "yes", "y", "sim", "on"}


def assert_escrita_ativa(session: Session) -> None:
    """Recusa qualquer criação enquanto o interruptor estiver desligado."""
    if not carregar_escrita_ativa(session):
        raise RuntimeError(
            "A escrita no iMos está desligada. Ative a definição "
            f"'{KEY_IMOS_ESCRITA_ATIVA}' em Configurações > Definições do sistema."
        )


def build_connection_string(cfg: ImosConfig) -> str:
    """Ligação de escrita: igual à de leitura, mas sem ``ApplicationIntent``.

    ``ApplicationIntent=ReadOnly`` faria o servidor recusar o INSERT, por isso
    é a única diferença. As credenciais são as mesmas já configuradas.
    """
    server = (cfg.get("server") or "").strip()
    database = (cfg.get("database") or "").strip()
    user = (cfg.get("user") or "").strip()
    password = str(cfg.get("password") or "")
    trusted = bool(cfg.get("trusted"))

    if not server or not database:
        raise ValueError(
            "Configuração iMos incompleta: servidor e base de dados são obrigatórios."
        )

    parts = [
        f"Server={_connection_value(server, 'Servidor')}",
        f"Database={_connection_value(database, 'Base de dados')}",
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


def _valor_texto(coluna: str, tamanho: int, valor: Any) -> str:
    """Normaliza um valor de texto e garante que cabe na coluna do iMos."""
    if valor is None:
        return ""
    texto = str(valor).replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    texto = texto.replace("\x00", "").strip()
    if len(texto) > tamanho:
        raise ValueError(
            f"O valor da coluna {coluna} tem {len(texto)} caracteres e o iMos "
            f"só aceita {tamanho}. Trunque o valor antes de criar o nó."
        )
    return texto


def _campos_normalizados(campos: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Valida as colunas pedidas e devolve-as prontas a parametrizar."""
    resultado: list[dict[str, Any]] = []
    for coluna_bruta, valor in (campos or {}).items():
        coluna = str(coluna_bruta or "").strip().upper()
        if coluna in COLUNAS_RESERVADAS:
            raise ValueError(
                f"A coluna {coluna} é gerida pelo motor e não pode ser indicada."
            )
        if coluna not in COLUNAS_PROADMIN:
            raise ValueError(f"Coluna desconhecida em dbo.PROADMIN: {coluna}.")

        tipo_sql, tamanho = COLUNAS_PROADMIN[coluna]
        if tipo_sql == "int":
            item = {"coluna": coluna, "tipo": "int", "tamanho": 0, "valor": int(valor or 0)}
        elif tipo_sql == "real":
            item = {
                "coluna": coluna,
                "tipo": "real",
                "tamanho": 0,
                "valor": float(valor or 0),
            }
        else:
            item = {
                "coluna": coluna,
                "tipo": "nvarchar",
                "tamanho": tamanho,
                "valor": _valor_texto(coluna, tamanho, valor),
            }
        resultado.append(item)

    resultado.sort(key=lambda item: item["coluna"])
    return resultado


def construir_payload(cfg: ImosConfig, nos: list[NoParaCriar]) -> dict[str, Any]:
    """Valida a lista de nós e devolve o payload pronto para execução.

    Separado da execução de propósito: toda a validação é testável sem tocar
    em SQL nenhum.
    """
    if not nos:
        raise ValueError("Não há nós para criar no iMos.")

    itens: list[dict[str, Any]] = []
    for indice, no in enumerate(nos):
        if not nome_imos_valido(no.nome):
            raise ValueError(
                f"Nome inválido para o iMos: {no.nome!r}. São permitidos até 30 "
                "caracteres em letras, algarismos, espaço e _ ( ) . -"
            )
        if no.tipo not in TIPOS_PERMITIDOS:
            raise ValueError(
                f"Tipo de nó não permitido: {no.tipo}. Só pasta "
                f"({IMOS_TIPO_PASTA}) ou encomenda ({IMOS_TIPO_ENCOMENDA})."
            )

        tem_dir = no.parent_dir_id is not None
        tem_indice = no.parent_indice is not None
        if tem_dir == tem_indice:
            raise ValueError(
                f"O nó {no.nome!r} tem de indicar exatamente um pai: "
                "parent_dir_id (já existe) ou parent_indice (criado agora)."
            )
        if tem_indice and not 0 <= int(no.parent_indice) < indice:
            raise ValueError(
                f"O nó {no.nome!r} aponta para um pai que ainda não foi criado."
            )
        if tem_dir and int(no.parent_dir_id) <= 0:
            raise ValueError(f"O nó {no.nome!r} tem um parent_dir_id inválido.")

        itens.append(
            {
                "nome": no.nome,
                "tipo": int(no.tipo),
                "parent_dir_id": int(no.parent_dir_id) if tem_dir else None,
                "parent_indice": int(no.parent_indice) if tem_indice else None,
                "campos": _campos_normalizados(no.campos),
            }
        )

    return {"conn": build_connection_string(cfg), "nos": itens}


_PS_SCRIPT = r"""
param(
  [Parameter(Mandatory=$true)][string]$PayloadB64
)
$ErrorActionPreference = 'Stop'

$payloadJson = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PayloadB64))
$p = $payloadJson | ConvertFrom-Json
$connStr = [string]$p.conn

# Segunda barreira, do lado do PowerShell: os nomes de coluna sao a unica
# parte do payload que entra no texto SQL, por isso sao validados aqui outra vez.
$colunasOk = @(COLUNAS_PERMITIDAS)
$tiposOk = @(TIPOS_PERMITIDOS)

Add-Type -AssemblyName System.Data
$conn = New-Object System.Data.SqlClient.SqlConnection $connStr
$conn.Open()
$tx = $conn.BeginTransaction()
try {
  $criados = @()
  $dirIds = @()

  foreach ($no in $p.nos) {
    if ($tiposOk -notcontains [int]$no.tipo) { throw ('Tipo de no nao permitido: ' + $no.tipo) }

    if ($null -ne $no.parent_indice) {
      $parent = [int]$dirIds[[int]$no.parent_indice]
    } else {
      $parent = [int]$no.parent_dir_id
    }
    if ($parent -le 0) { throw ('Pai invalido para o no ' + $no.nome) }

    # 1) linha da arvore; o DIR_ID vem do IDENTITY
    $cmd = $conn.CreateCommand()
    $cmd.Transaction = $tx
    $cmd.CommandText = 'INSERT INTO dbo.IMORDFOLDER (NAME, TYPE, PARENT_ID, STATUS, USERGROUP_ID) VALUES (@nome, @tipo, @parent, 0, 0); SELECT CAST(SCOPE_IDENTITY() AS int);'
    $par = $cmd.Parameters.Add('@nome', [System.Data.SqlDbType]::NVarChar, 30)
    $par.Value = [string]$no.nome
    $par = $cmd.Parameters.Add('@tipo', [System.Data.SqlDbType]::Int)
    $par.Value = [int]$no.tipo
    $par = $cmd.Parameters.Add('@parent', [System.Data.SqlDbType]::Int)
    $par.Value = $parent
    $dir = [int]$cmd.ExecuteScalar()
    if ($dir -le 0) { throw ('Nao foi devolvido DIR_ID para o no ' + $no.nome) }

    # 2) linha de dados; PRODUCTIONID tem de ser o DIR_ID acabado de gerar
    $colunas = @('NAME','TYPE','PRODUCTIONID','DATECREATE','LCHANGE')
    $valores = @('@nome','@tipo','@prodid','GETDATE()','GETDATE()')
    $cmd2 = $conn.CreateCommand()
    $cmd2.Transaction = $tx
    $par = $cmd2.Parameters.Add('@nome', [System.Data.SqlDbType]::NVarChar, 30)
    $par.Value = [string]$no.nome
    $par = $cmd2.Parameters.Add('@tipo', [System.Data.SqlDbType]::Int)
    $par.Value = [int]$no.tipo
    $par = $cmd2.Parameters.Add('@prodid', [System.Data.SqlDbType]::Int)
    $par.Value = $dir

    $i = 0
    foreach ($campo in $no.campos) {
      $coluna = [string]$campo.coluna
      if ($colunasOk -notcontains $coluna) { throw ('Coluna nao permitida: ' + $coluna) }
      $nomeParam = '@c' + $i
      $colunas += $coluna
      $valores += $nomeParam
      switch ([string]$campo.tipo) {
        'int' {
          $par = $cmd2.Parameters.Add($nomeParam, [System.Data.SqlDbType]::Int)
          $par.Value = [int]$campo.valor
        }
        'real' {
          $par = $cmd2.Parameters.Add($nomeParam, [System.Data.SqlDbType]::Real)
          $par.Value = [single]$campo.valor
        }
        default {
          $par = $cmd2.Parameters.Add($nomeParam, [System.Data.SqlDbType]::NVarChar, [int]$campo.tamanho)
          $par.Value = [string]$campo.valor
        }
      }
      $i = $i + 1
    }
    $cmd2.CommandText = 'INSERT INTO dbo.PROADMIN (' + ($colunas -join ', ') + ') VALUES (' + ($valores -join ', ') + '); SELECT CAST(SCOPE_IDENTITY() AS int);'
    $proadminId = [int]$cmd2.ExecuteScalar()

    $dirIds += $dir
    $criados += [pscustomobject]@{
      nome = [string]$no.nome
      tipo = [int]$no.tipo
      dir_id = $dir
      proadmin_id = $proadminId
      parent_dir_id = $parent
    }
  }

  $tx.Commit()
  $json = ConvertTo-Json -InputObject @($criados) -Depth 6 -Compress
  [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
} catch {
  try { $tx.Rollback() } catch { }
  throw
} finally {
  $conn.Close()
}
"""


def _powershell_script() -> str:
    """Injeta as listas brancas no script, entre aspas simples do PowerShell."""
    colunas = ",".join(f"'{coluna}'" for coluna in sorted(COLUNAS_PROADMIN))
    tipos = ",".join(str(tipo) for tipo in TIPOS_PERMITIDOS)
    return _PS_SCRIPT.replace("COLUNAS_PERMITIDAS", colunas).replace(
        "TIPOS_PERMITIDOS", tipos
    )


def executar_payload(payload: dict[str, Any]) -> list[NoCriado]:
    """Corre a transação de criação via PowerShell + System.Data.SqlClient."""
    payload_b64 = base64.b64encode(
        json.dumps(payload, ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".ps1", delete=False
        ) as tf:
            tf.write(_powershell_script())
            temp_path = tf.name

        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        )
        result = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                temp_path,
                payload_b64,
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            raise RuntimeError(
                "\n".join(s for s in (stderr, stdout) if s)
                or f"Codigo de saida: {result.returncode}"
            )

        raw_b64 = (result.stdout or "").strip()
        if not raw_b64:
            return []

        dados = json.loads(base64.b64decode(raw_b64).decode("utf-8", errors="replace"))
        if isinstance(dados, dict):
            dados = [dados]
        return [
            NoCriado(
                nome=str(item.get("nome") or ""),
                tipo=int(item.get("tipo") or 0),
                dir_id=int(item.get("dir_id") or 0),
                proadmin_id=int(item.get("proadmin_id") or 0),
                parent_dir_id=int(item.get("parent_dir_id") or 0),
            )
            for item in dados
        ]
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def criar_nos(
    session: Session, cfg: ImosConfig, nos: list[NoParaCriar]
) -> list[NoCriado]:
    """Cria os nós indicados no iMos, todos na mesma transação.

    Só corre com o interruptor ``imos_escrita_ativa`` ligado. Se qualquer nó
    falhar, a transação é revertida e nada fica criado.
    """
    assert_escrita_ativa(session)
    return executar_payload(construir_payload(cfg, nos))


def explicar_erro_escrita(exc: Exception) -> str:
    """Converte erros do SqlClient numa mensagem útil, sem detalhe técnico."""
    detalhe = str(exc or "")
    normalizado = detalhe.casefold()
    if "permission was denied" in normalizado or "permissão" in normalizado:
        return (
            "O SQL Server recusou a escrita: a conta configurada não tem "
            "permissão de INSERT em dbo.IMORDFOLDER / dbo.PROADMIN."
        )
    if "read-only" in normalizado or "somente leitura" in normalizado:
        return (
            "A ligação foi aberta em modo só-leitura. Confirme que a base de "
            "dados iMos não está marcada como read-only no servidor."
        )
    if "string or binary data would be truncated" in normalizado:
        return (
            "Um dos valores é maior do que a coluna do iMos permite. Reveja o "
            "nome e os campos antes de voltar a tentar."
        )
    if "login failed" in normalizado:
        return (
            "O servidor SQL recusou o utilizador/password configurados na "
            "Ligação iMos."
        )
    # Mantém a mensagem original quando não há tradução conhecida: é a única
    # pista útil quando algo corre mal a meio de uma transação.
    return re.sub(r"[A-Za-z]:\\[^\s]+\.ps1[: ]*", "", detalhe).strip() or (
        "Não foi possível criar a encomenda no iMos."
    )
