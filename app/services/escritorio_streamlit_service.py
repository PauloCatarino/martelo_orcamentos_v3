"""Escritório do Streamlit — leituras (só SELECT).

Lê na base do Streamlit o que é preciso para decidir se um modelo/versão pode
seguir do Desenho para o Aprovisionamento (:func:`avaliar`) e, no sentido
contrário, que obras em Desenho no Martelo o Escritório já avançou
(:func:`levantar_sugestoes`). A escrita está à parte, em
:mod:`app.services.escritorio_streamlit_escrita`.

Todas as consultas de um pedido vão juntas numa só ida ao servidor (um só
PowerShell): no Gravar da Produção cada segundo conta. Os valores viajam como
parâmetros tipados, e cada consulta passa pela barreira «só SELECT» em Python
e outra vez no PowerShell, como em :mod:`app.services.phc_sql`.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain import escritorio_streamlit as regras
from app.domain.escritorio_streamlit import Avaliacao, ChaveVersao, DadosEscritorio
from app.models.producao import Producao
from app.services import streamlit_sql_service as st
from app.services.phc_sql import assert_select_only
from app.services.system_setting_service import SystemSettingService

#: Interruptor da escrita (Configurações › Caminhos do Sistema). Desligado por
#: omissão: a mesma conta SQL serve todas as leituras do Martelo, por isso é
#: isto — e não a conta — que impede o Martelo de escrever no Streamlit.
KEY_STREAMLIT_ESCRITA_ATIVA = "streamlit_escrita_ativa"

#: Correção à mão da ligação Martelo → Streamlit (``paulo=paulo_catarino``).
KEY_STREAMLIT_MAPA_UTILIZADORES = "streamlit_mapa_utilizadores"

#: Segundos para abrir a ligação. O servidor do Streamlit é um PC: se estiver
#: desligado, o Gravar não pode ficar um minuto à espera.
TIMEOUT_LIGACAO_S = 8

#: Tempo máximo do PowerShell inteiro.
TIMEOUT_PROCESSO_S = 60


@dataclass(frozen=True)
class Consulta:
    nome: str
    sql: str


# ---------------------------------------------------------------------------
# Definições
# ---------------------------------------------------------------------------
def escrita_ativa(session: Session) -> bool:
    valor = SystemSettingService(session).obter_valor(KEY_STREAMLIT_ESCRITA_ATIVA, "")
    return regras.verdadeiro(valor)


def mapa_utilizadores(session: Session) -> dict[str, str]:
    return regras.ler_mapa_utilizadores(
        SystemSettingService(session).obter_valor(KEY_STREAMLIT_MAPA_UTILIZADORES, "")
    )


def ligacao(session: Session) -> str:
    """Connection string do Streamlit, com o tempo de ligação curto."""
    return st.build_connection_string(
        st.load_streamlit_config(session), timeout=TIMEOUT_LIGACAO_S
    )


# ---------------------------------------------------------------------------
# PowerShell
# ---------------------------------------------------------------------------
def correr_powershell(script: str, payload: Mapping[str, Any], *, timeout: int) -> Any:
    """Corre ``script`` com o ``payload`` (JSON em base64) e devolve o JSON lido.

    O script escreve o resultado em base64 no stdout; um erro sai pelo código
    de saída e pelo stderr.
    """
    payload_b64 = base64.b64encode(
        json.dumps(dict(payload), ensure_ascii=False).encode("utf-8")
    ).decode("ascii")

    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".ps1", delete=False
        ) as ficheiro:
            ficheiro.write(script)
            temp_path = ficheiro.name

        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        resultado = subprocess.run(
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
            timeout=timeout,
            creationflags=creationflags,
        )
        if resultado.returncode != 0:
            detalhe = "\n".join(
                s for s in ((resultado.stderr or "").strip(), (resultado.stdout or "").strip()) if s
            )
            raise RuntimeError(detalhe or f"Codigo de saida: {resultado.returncode}")

        bruto = (resultado.stdout or "").strip()
        if not bruto:
            return None
        return json.loads(base64.b64decode(bruto).decode("utf-8", errors="replace"))
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


_PS_LEITURA = r"""
param(
  [Parameter(Mandatory=$true)][string]$PayloadB64
)
$ErrorActionPreference = 'Stop'

$payloadJson = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PayloadB64))
$p = $payloadJson | ConvertFrom-Json

# Segunda barreira, do lado do PowerShell: so' SELECT, um comando de cada vez.
$banned = @('INSERT','UPDATE','DELETE','DROP','ALTER','TRUNCATE','MERGE','EXEC','CREATE','INTO','GRANT','REVOKE','DENY')
foreach ($c in $p.consultas) {
  $q = ([string]$c.sql).Trim()
  if (-not $q.ToUpper().StartsWith('SELECT')) { throw 'Consulta invalida: apenas SELECT e permitido.' }
  if ($q.TrimEnd(';').Contains(';')) { throw 'Consulta invalida: multiplos statements nao sao permitidos.' }
  foreach ($t in $banned) {
    if ([regex]::IsMatch($q, ('\b' + $t + '\b'), [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)) {
      throw 'Consulta invalida: apenas SELECT e permitido.'
    }
  }
}

Add-Type -AssemblyName System.Data
$conn = New-Object System.Data.SqlClient.SqlConnection ([string]$p.conn)
$conn.Open()
try {
  $saida = [ordered]@{}
  foreach ($c in $p.consultas) {
    $cmd = $conn.CreateCommand()
    $cmd.CommandText = [string]$c.sql
    $cmd.CommandTimeout = 30
    foreach ($par in $p.parametros) {
      if ([string]$par.tipo -eq 'int') {
        $x = $cmd.Parameters.Add([string]$par.nome, [System.Data.SqlDbType]::Int)
        $x.Value = [int]$par.valor
      } else {
        $x = $cmd.Parameters.Add([string]$par.nome, [System.Data.SqlDbType]::NVarChar, [int]$par.tamanho)
        $x.Value = [string]$par.valor
      }
    }
    $dt = New-Object System.Data.DataTable
    $da = New-Object System.Data.SqlClient.SqlDataAdapter $cmd
    [void]$da.Fill($dt)
    $linhas = New-Object System.Collections.ArrayList
    foreach ($r in $dt.Rows) {
      $obj = [ordered]@{}
      foreach ($col in $dt.Columns) {
        $v = $r[$col.ColumnName]
        if ($v -is [System.DBNull]) { $v = $null }
        $obj[$col.ColumnName] = $v
      }
      [void]$linhas.Add([pscustomobject]$obj)
    }
    $saida[[string]$c.nome] = $linhas
  }
  $json = ConvertTo-Json -InputObject ([pscustomobject]$saida) -Depth 6 -Compress
  [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
} finally {
  $conn.Close()
}
"""


def _linhas(valor: Any) -> list[dict[str, Any]]:
    """O PowerShell 5.1 às vezes desembrulha listas de um elemento."""
    if valor is None:
        return []
    if isinstance(valor, dict):
        return [valor]
    if isinstance(valor, list):
        return [linha for linha in valor if isinstance(linha, dict)]
    return []


def ler_consultas(
    conn: str,
    consultas: Sequence[Consulta],
    parametros: Sequence[Mapping[str, Any]] = (),
) -> dict[str, list[dict[str, Any]]]:
    """Corre as consultas (só SELECT) numa só ligação e devolve as linhas de cada."""
    for consulta in consultas:
        assert_select_only(consulta.sql)
    dados = correr_powershell(
        _PS_LEITURA,
        {
            "conn": conn,
            "consultas": [{"nome": c.nome, "sql": c.sql} for c in consultas],
            "parametros": [dict(p) for p in parametros],
        },
        timeout=TIMEOUT_PROCESSO_S,
    )
    dados = dados if isinstance(dados, dict) else {}
    return {consulta.nome: _linhas(dados.get(consulta.nome)) for consulta in consultas}


def _primeira(linhas: list[dict[str, Any]]) -> dict[str, Any] | None:
    return linhas[0] if linhas else None


# ---------------------------------------------------------------------------
# Martelo → Streamlit: pode este modelo/versão avançar?
# ---------------------------------------------------------------------------
_COLUNAS_DATA_VERSAO = (
    "CONVERT(VARCHAR(19), desenho_concluido_em, 126) AS desenho_concluido_em, "
    "libertada_por, CONVERT(VARCHAR(19), libertada_em, 126) AS libertada_em"
)


def parametros_da_chave(chave: ChaveVersao) -> list[dict[str, Any]]:
    return [
        {"nome": "@ano", "tipo": "int", "valor": chave.ano},
        {"nome": "@numero", "tipo": "nvarchar", "tamanho": regras.LIMITE_NUMERO, "valor": chave.numero},
        {"nome": "@bd_key", "tipo": "nvarchar", "tamanho": regras.LIMITE_BD_KEY, "valor": chave.bd_key},
    ]


def consultas_do_envio(chave: ChaveVersao) -> list[Consulta]:
    """As leituras do Streamlit antes de avançar (secção 5.1 do contrato).

    Os nomes das tabelas gémeas (``_``) saem de uma lista fechada, nunca do
    texto da obra.
    """
    sufixo = "_" if chave.sufixo == "_" else ""
    caderno = f"dbo.CadernoEncargos{sufixo}"
    tempos = f"dbo.TemposProducao{sufixo}"
    return [
        Consulta(
            "obra",
            "SELECT estado_obra, desenhador_username FROM dbo.Escritorio_Obras "
            "WHERE ano = @ano AND numero = @numero",
        ),
        Consulta(
            "versao",
            "SELECT etapa, desenho_concluido_por, "
            + _COLUNAS_DATA_VERSAO
            + " FROM dbo.Escritorio_Versoes WHERE bd_key = @bd_key",
        ),
        Consulta(
            "ultimo_avanco",
            "SELECT TOP 1 utilizador, detalhe, CONVERT(VARCHAR(19), criado_em, 126) AS criado_em "
            "FROM dbo.Escritorio_Eventos WHERE bd_key = @bd_key AND tipo = 'AVANCAR' "
            "ORDER BY id DESC",
        ),
        Consulta(
            "ce",
            "SELECT bd_ano, bd_n_encomenda, bd_cliente, bd_placas_cl, bd_placas_le, "
            "bd_placas_ambos, bd_de_quem_orla_cl, bd_de_quem_orla_le, bd_de_quem_orla_ambos, "
            "CASE WHEN LEN(LTRIM(RTRIM(ISNULL(bd_materias, N'')))) > 0 THEN 1 ELSE 0 END "
            f"AS tem_materias FROM {caderno} WHERE bd_key = @bd_key",
        ),
        Consulta(
            "tp",
            "SELECT bd_plano_corte, bd_status_envio, bd_assistencia "
            f"FROM {tempos} WHERE bd_key = @bd_key",
        ),
        # Nunca a password_hash: só o que serve para saber quem pode enviar.
        Consulta(
            "utilizadores",
            "SELECT username, nome, permissoes, is_admin, ativo, local_trabalho "
            "FROM dbo.Utilizadores WHERE ativo = 1",
        ),
        Consulta(
            "locais",
            "SELECT Nome, Permissoes, Ativo FROM dbo.LocaisTrabalho WHERE Ativo = 1",
        ),
    ]


def avaliar(
    session: Session,
    chave: ChaveVersao,
    *,
    martelo_username: str,
    martelo_nome: str,
) -> Avaliacao:
    """Ler o Streamlit e decidir. Só lê: é também o «modo simulação».

    As recusas que não precisam do servidor (assistências, versão ≠ 01)
    respondem logo, sem ligação nenhuma.
    """
    local = regras.recusa_sem_ir_ao_streamlit(chave)
    if local:
        return regras.avaliar_envio(chave, DadosEscritorio(), None)

    mapa = mapa_utilizadores(session)
    linhas = ler_consultas(ligacao(session), consultas_do_envio(chave), parametros_da_chave(chave))
    utilizadores = regras.utilizadores_streamlit(linhas["utilizadores"], linhas["locais"])
    utilizador, mensagem = regras.resolver_utilizador(
        martelo_username, martelo_nome, utilizadores, mapa
    )
    dados = DadosEscritorio(
        obra=_primeira(linhas["obra"]),
        versao=_primeira(linhas["versao"]),
        ultimo_avanco=_primeira(linhas["ultimo_avanco"]),
        ce=_primeira(linhas["ce"]),
        tp=_primeira(linhas["tp"]),
        utilizadores=tuple(utilizadores),
    )
    return regras.avaliar_envio(chave, dados, utilizador, mensagem)


# ---------------------------------------------------------------------------
# Streamlit → Martelo: o que o Escritório já avançou
# ---------------------------------------------------------------------------
CONSULTA_TOKEN = Consulta(
    "token", "SELECT MAX(id) AS max_id FROM dbo.Escritorio_Eventos"
)

CONSULTA_AVANCADAS = Consulta(
    "versoes",
    "SELECT bd_key, etapa, desenho_concluido_por, "
    + _COLUNAS_DATA_VERSAO
    + " FROM dbo.Escritorio_Versoes WHERE etapa IN ('APROVISIONAMENTO', 'LIBERTADA')",
)


def _token(linhas: list[dict[str, Any]]) -> int | None:
    linha = _primeira(linhas) or {}
    try:
        return int(linha.get("max_id"))
    except (TypeError, ValueError):
        return None


def ler_token(session: Session) -> int | None:
    """O ``MAX(id)`` dos eventos: muda sempre que alguém faz algo no Escritório.

    É a pergunta barata que se faz de cinco em cinco minutos; só quando muda é
    que vale a pena ir buscar as versões.
    """
    linhas = ler_consultas(ligacao(session), [CONSULTA_TOKEN])
    return _token(linhas["token"])


def _processos_da_pessoa(session: Session, responsavel: str | None) -> list[Producao]:
    """As obras de ``responsavel`` (todas, se vazio); o estado filtra-se depois."""
    processos = session.execute(select(Producao)).scalars().all()
    alvo = (responsavel or "").strip().casefold()
    resultado = []
    for processo in processos:
        if alvo and (processo.responsavel or "").strip().casefold() != alvo:
            continue
        resultado.append(processo)
    return resultado


def levantar_sugestoes(
    session: Session, *, responsavel: str | None = None
) -> tuple[int | None, list[dict[str, Any]]]:
    """Obras (de ``responsavel``) em Desenho que o Escritório já avançou.

    Devolve também o token lido, para a próxima vez só se perguntar se mudou.
    """
    linhas = ler_consultas(ligacao(session), [CONSULTA_TOKEN, CONSULTA_AVANCADAS])
    versoes = {
        str(linha.get("bd_key") or "").strip(): linha
        for linha in linhas["versoes"]
        if str(linha.get("bd_key") or "").strip()
    }
    processos = _processos_da_pessoa(session, responsavel)
    return _token(linhas["token"]), regras.sugestoes_de_producao(processos, versoes)


# ---------------------------------------------------------------------------
# Erros
# ---------------------------------------------------------------------------
def explicar_erro_leitura(exc: BaseException) -> str:
    """Mensagem curta para o utilizador, sem connection strings nem caminhos."""
    detalhe = str(exc or "")
    normal = detalhe.casefold()
    if isinstance(exc, subprocess.TimeoutExpired) or "timeout" in normal or "tempo limite" in normal:
        return "O Streamlit não respondeu a tempo (o servidor pode estar desligado)."
    if (
        "network-related" in normal
        or "server was not found" in normal
        or "não foi encontrado" in normal
        or "could not open a connection" in normal
    ):
        return "Não consegui ligar ao servidor do Streamlit (desligado ou fora da rede)."
    if "login failed" in normal:
        return "O servidor do Streamlit recusou o utilizador/password configurados."
    if "invalid object name" in normal and "escritorio" in normal:
        return "O Escritório ainda não está instalado na base do Streamlit."
    if "permission was denied" in normal:
        return "A conta SQL do Martelo não tem permissão para esta operação no Streamlit."
    if "configuracao streamlit incompleta" in regras.sem_acentos(detalhe):
        return detalhe
    return re.sub(r"[A-Za-z]:\\[^\s]+\.ps1[: ]*", "", detalhe).strip()[:400] or (
        "Erro técnico ao falar com o Streamlit."
    )
