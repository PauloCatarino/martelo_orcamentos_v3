"""Único canal de escrita do Martelo na base do Streamlit (Escritório).

Faz uma coisa só: o passo «Enviar para o Aprovisionamento» de UM modelo/versão
— ``Escritorio_Versoes`` de ``DESENHO`` para ``APROVISIONAMENTO``, mais o
evento ``AVANCAR`` com ``"via": "MARTELO"`` — e, quando o material é só do
cliente, a libertação automática que o próprio Streamlit faz nesse caso. No
fim deixa a linha de espelho no Histórico do Tempos de Produção.

Barreiras, como na escrita do iMos (:mod:`app.services.imos_escrita`):

1. O interruptor ``streamlit_escrita_ativa``, desligado por omissão. A conta
   SQL do Martelo pode escrever nestas quatro tabelas (desde 28-10-2026) e é a
   mesma de todas as leituras: o interruptor é o que segura tudo.
2. O SQL é fixo, escrito aqui. Não há nenhum caminho de código que produza
   ``DELETE``, ``DROP`` ou ``ALTER``, nem que mexa noutras tabelas. Nunca se
   altera nem apaga um evento: só se acrescentam.
3. Os valores viajam como parâmetros tipados com o comprimento da coluna; o
   único nome que muda — a tabela gémea do histórico — sai de uma lista
   fechada, verificada também no PowerShell.
4. Tudo numa transação: o ``UPDATE`` só passa se a etapa ainda for
   ``DESENHO`` (outra pessoa pode ter-se adiantado), e o ``command_id`` do
   clique é único na base — o mesmo clique nunca grava duas vezes.

As horas do Escritório são do servidor e em UTC (``SYSUTCDATETIME()``); a do
histórico é a hora local do servidor (``GETDATE()``), como no Streamlit.
"""

from __future__ import annotations

import socket
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.config.versao import VERSAO_APLICACAO
from app.domain import escritorio_streamlit as regras
from app.domain.escritorio_streamlit import Avaliacao
from app.services import escritorio_streamlit_service as leitura

GRAVADO = "gravado"
JA_REGISTADO = "ja_registado"
CONFLITO = "conflito"

#: Colunas do histórico (``TemposProducaoHistorico``) e o seu comprimento.
_LIMITES_ESPELHO = {
    "bd_key": 255,
    "bd_ano": 50,
    "bd_n_encomenda": 100,
    "bd_cliente": 255,
    "bd_plano_corte": 255,
    "responsavel": 100,
    "comentarios": regras.LIMITE_COMENTARIOS,
}


@dataclass(frozen=True)
class ResultadoEnvio:
    resultado: str
    libertada: bool = False
    espelho: int = 0
    espelho_erro: str = ""
    ensaio: bool = False

    @property
    def gravado(self) -> bool:
        return self.resultado == GRAVADO


def assert_escrita_ativa(session: Session) -> None:
    if not leitura.escrita_ativa(session):
        raise RuntimeError(
            "O envio para o Aprovisionamento (Streamlit) está desligado. O "
            "administrador liga-o em Configurações › Caminhos do Sistema › "
            f"{leitura.KEY_STREAMLIT_ESCRITA_ATIVA} (ON)."
        )


def _texto(valor: Any, limite: int, campo: str) -> str:
    texto = str(valor or "").replace("\x00", "").strip()
    if len(texto) > limite:
        raise ValueError(f"{campo} tem {len(texto)} caracteres; o Streamlit aceita {limite}.")
    return texto


def _cortar(valor: Any, limite: int) -> str:
    """Para o espelho: um registo de histórico pode perder a ponta, não falhar."""
    return str(valor if valor is not None else "").replace("\x00", "").strip()[:limite]


def construir_payload(
    conn: str,
    avaliacao: Avaliacao,
    *,
    command_id: str,
    versao_programa: str = "",
    posto: str = "",
    pasta: str = "",
    ensaio: bool = False,
) -> dict[str, Any]:
    """Tudo o que a transação precisa, já validado. Não toca na base."""
    if not avaliacao.pronto:
        raise ValueError(f"Este modelo/versão não pode avançar: {avaliacao.mensagem}")
    try:
        uuid.UUID(str(command_id))
    except ValueError as erro:
        raise ValueError("command_id inválido.") from erro

    chave = avaliacao.chave
    utilizador = _texto(avaliacao.utilizador, regras.LIMITE_UTILIZADOR, "O utilizador")
    if not utilizador:
        raise ValueError("Falta o utilizador do Streamlit.")
    desenhador = avaliacao.desenhador
    if desenhador is not None:
        desenhador = _texto(desenhador, regras.LIMITE_UTILIZADOR, "O desenhador")

    detalhe = regras.detalhe_avancar(
        chave,
        versao_programa=versao_programa,
        posto=posto,
        em_nome_de=avaliacao.em_nome_de,
        avisos_aceites=avaliacao.avisos,
        pasta=pasta,
    )
    eventos: list[dict[str, Any]] = [
        {
            "tipo": "AVANCAR",
            "de": regras.ETAPA_DESENHO,
            "para": regras.ETAPA_APROVISIONAMENTO,
            "utilizador": utilizador,
            "motivo": _texto(regras.MOTIVO_AVANCAR, regras.LIMITE_MOTIVO, "O motivo"),
            "detalhe": regras.json_detalhe(detalhe),
            "command_id": _texto(command_id, regras.LIMITE_COMMAND_ID, "O command_id"),
            "espelho": regras.texto_espelho(
                regras.ROTULO_AVANCAR, via=regras.VIA_MARTELO, motivo=regras.MOTIVO_AVANCAR
            ),
        }
    ]
    if avaliacao.material_cliente:
        eventos.append(
            {
                "tipo": "LIBERTAR_AUTO",
                "de": regras.ETAPA_APROVISIONAMENTO,
                "para": regras.ETAPA_LIBERTADA,
                "utilizador": regras.UTILIZADOR_SISTEMA,
                "motivo": _texto(regras.MOTIVO_LIBERTAR_AUTO, regras.LIMITE_MOTIVO, "O motivo"),
                "detalhe": regras.json_detalhe(
                    regras.detalhe_libertar_auto(
                        chave, material=avaliacao.material_cliente, acionado_por=utilizador
                    )
                ),
                "command_id": regras.id_filho(command_id, chave.bd_key),
                "espelho": regras.texto_espelho(
                    regras.ROTULO_LIBERTAR_AUTO,
                    via=regras.VIA_MARTELO,
                    motivo=regras.MOTIVO_LIBERTAR_AUTO,
                ),
            }
        )

    ce = avaliacao.ce or {}
    return {
        "conn": conn,
        "ensaio": bool(ensaio),
        "bd_key": chave.bd_key,
        "ano": chave.ano,
        "numero": chave.numero,
        "modelo": chave.modelo,
        "versao": chave.versao,
        "sufixo": chave.sufixo,
        "utilizador": utilizador,
        "desenhador": desenhador,
        "eventos": eventos,
        "espelho": {
            "bd_key": _cortar(chave.bd_key, _LIMITES_ESPELHO["bd_key"]),
            "bd_ano": _cortar(ce.get("bd_ano") or chave.ano, _LIMITES_ESPELHO["bd_ano"]),
            "bd_n_encomenda": _cortar(
                ce.get("bd_n_encomenda") or chave.numero, _LIMITES_ESPELHO["bd_n_encomenda"]
            ),
            "bd_cliente": _cortar(ce.get("bd_cliente"), _LIMITES_ESPELHO["bd_cliente"]),
            "bd_plano_corte": _cortar(avaliacao.plano_corte, _LIMITES_ESPELHO["bd_plano_corte"]),
        },
    }


_PS_ESCRITA = r"""
param(
  [Parameter(Mandatory=$true)][string]$PayloadB64
)
$ErrorActionPreference = 'Stop'

$payloadJson = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PayloadB64))
$p = $payloadJson | ConvertFrom-Json

# A unica parte variavel do texto SQL: a tabela gemea do historico.
$sufixo = [string]$p.sufixo
if ($sufixo -ne '' -and $sufixo -ne '_') { throw 'Sufixo de tabela invalido.' }
$tabelaHistorico = 'dbo.TemposProducaoHistorico' + $sufixo
$tiposOk = @('AVANCAR', 'LIBERTAR_AUTO')

function Novo-Comando($conn, $tx, [string]$sql) {
  $c = $conn.CreateCommand()
  $c.Transaction = $tx
  $c.CommandText = $sql
  $c.CommandTimeout = 30
  return $c
}

function Add-Texto($cmd, [string]$nome, [int]$tamanho, $valor) {
  $x = $cmd.Parameters.Add($nome, [System.Data.SqlDbType]::NVarChar, $tamanho)
  if ($null -eq $valor) { $x.Value = [System.DBNull]::Value } else { $x.Value = [string]$valor }
}

function Add-Inteiro($cmd, [string]$nome, $valor) {
  $x = $cmd.Parameters.Add($nome, [System.Data.SqlDbType]::Int)
  $x.Value = [int]$valor
}

function Saida($resultado, $libertada, $espelho, $espelhoErro) {
  $o = [pscustomobject]@{
    resultado = [string]$resultado
    libertada = [bool]$libertada
    espelho = [int]$espelho
    espelho_erro = [string]$espelhoErro
    ensaio = [bool]$p.ensaio
  }
  $json = ConvertTo-Json -InputObject $o -Compress
  [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($json))
}

foreach ($ev in $p.eventos) {
  if ($tiposOk -notcontains [string]$ev.tipo) { throw ('Tipo de evento nao permitido: ' + $ev.tipo) }
}

Add-Type -AssemblyName System.Data
$conn = New-Object System.Data.SqlClient.SqlConnection ([string]$p.conn)
$conn.Open()
try {
  $tx = $conn.BeginTransaction()
  $libertada = $false
  try {
    # 0) o mesmo clique ja' gravado?
    $c = Novo-Comando $conn $tx 'SELECT COUNT(*) FROM dbo.Escritorio_Eventos WHERE command_id = @cmd'
    Add-Texto $c '@cmd' 64 $p.eventos[0].command_id
    if ([int]$c.ExecuteScalar() -gt 0) {
      $tx.Rollback()
      Saida 'ja_registado' $false 0 ''
      return
    }

    # a) a linha nasce em DESENHO se ainda nao existe (como o Streamlit)
    $c = Novo-Comando $conn $tx ("INSERT INTO dbo.Escritorio_Versoes (bd_key, ano, numero, modelo, versao, etapa, preexistente, criada_em, criada_por, desenho_concluido_por, desenho_concluido_em, libertada_por, libertada_em, libertada_excecao, motivo_excecao, atualizado_em) " +
      "SELECT @k, @ano, @numero, @modelo, @versao, 'DESENHO', 0, SYSUTCDATETIME(), @quem, N'', NULL, N'', NULL, 0, N'', SYSUTCDATETIME() " +
      "WHERE NOT EXISTS (SELECT 1 FROM dbo.Escritorio_Versoes WITH (UPDLOCK, HOLDLOCK) WHERE bd_key = @k)")
    Add-Texto $c '@k' 60 $p.bd_key
    Add-Inteiro $c '@ano' $p.ano
    Add-Texto $c '@numero' 20 $p.numero
    Add-Texto $c '@modelo' 10 $p.modelo
    Add-Texto $c '@versao' 10 $p.versao
    Add-Texto $c '@quem' 100 $p.utilizador
    [void]$c.ExecuteNonQuery()

    # b) avancar, so' se ninguem se adiantou (compare-and-set sobre a etapa)
    $c = Novo-Comando $conn $tx ("UPDATE dbo.Escritorio_Versoes SET etapa = 'APROVISIONAMENTO', desenho_concluido_por = @quem, " +
      "desenho_concluido_em = SYSUTCDATETIME(), atualizado_em = SYSUTCDATETIME() WHERE bd_key = @k AND etapa = 'DESENHO'")
    Add-Texto $c '@k' 60 $p.bd_key
    Add-Texto $c '@quem' 100 $p.utilizador
    if ($c.ExecuteNonQuery() -ne 1) {
      $tx.Rollback()
      Saida 'conflito' $false 0 ''
      return
    }

    foreach ($ev in $p.eventos) {
      if ([string]$ev.tipo -eq 'LIBERTAR_AUTO') {
        # d) material so' do cliente: nao passa pelo Aprovisionamento
        $c = Novo-Comando $conn $tx ("UPDATE dbo.Escritorio_Versoes SET etapa = 'LIBERTADA', libertada_por = N'sistema', " +
          "libertada_em = SYSUTCDATETIME(), atualizado_em = SYSUTCDATETIME() WHERE bd_key = @k AND etapa = 'APROVISIONAMENTO'")
        Add-Texto $c '@k' 60 $p.bd_key
        if ($c.ExecuteNonQuery() -ne 1) { throw 'A libertacao automatica nao encontrou a versao no Aprovisionamento.' }
        $libertada = $true
      }
      # c) o evento (so' se acrescenta; nunca se altera)
      $c = Novo-Comando $conn $tx ("INSERT INTO dbo.Escritorio_Eventos (ano, numero, bd_key, tipo, de_etapa, para_etapa, desenhador_username, utilizador, motivo, detalhe, command_id, criado_em) " +
        "VALUES (@ano, @numero, @k, @tipo, @de, @para, @desenhador, @utilizador, @motivo, @detalhe, @cmd, SYSUTCDATETIME())")
      Add-Inteiro $c '@ano' $p.ano
      Add-Texto $c '@numero' 20 $p.numero
      Add-Texto $c '@k' 60 $p.bd_key
      $x = $c.Parameters.Add('@tipo', [System.Data.SqlDbType]::VarChar, 30); $x.Value = [string]$ev.tipo
      $x = $c.Parameters.Add('@de', [System.Data.SqlDbType]::VarChar, 20); $x.Value = [string]$ev.de
      $x = $c.Parameters.Add('@para', [System.Data.SqlDbType]::VarChar, 20); $x.Value = [string]$ev.para
      Add-Texto $c '@desenhador' 100 $p.desenhador
      Add-Texto $c '@utilizador' 100 $ev.utilizador
      Add-Texto $c '@motivo' 500 $ev.motivo
      Add-Texto $c '@detalhe' -1 $ev.detalhe
      Add-Texto $c '@cmd' 64 $ev.command_id
      [void]$c.ExecuteNonQuery()
    }

    if ($p.ensaio) {
      # Ensaio: tudo correu, nada fica.
      $tx.Rollback()
      Saida 'gravado' $libertada 0 ''
      return
    }
    $tx.Commit()
  } catch {
    try { $tx.Rollback() } catch { }
    # O PowerShell embrulha as excecoes do .NET: procurar a do SQL Server.
    $erro = $_.Exception
    while ($null -ne $erro -and -not ($erro -is [System.Data.SqlClient.SqlException])) {
      $erro = $erro.InnerException
    }
    if ($null -ne $erro -and ($erro.Number -eq 2601 -or $erro.Number -eq 2627)) {
      # Chave repetida: o mesmo clique (indice do command_id) ou outra pessoa
      # que criou a linha da versao no mesmo instante.
      if ($erro.Message -match 'command_id') { Saida 'ja_registado' $false 0 '' } else { Saida 'conflito' $false 0 '' }
      return
    }
    throw
  }

  # Depois do commit: o espelho no Historico do Tempos de Producao. Numa
  # transacao propria -- se falhar, o avanco fica na mesma.
  $espelho = 0
  $espelhoErro = ''
  try {
    $tx2 = $conn.BeginTransaction()
    foreach ($ev in $p.eventos) {
      $c = Novo-Comando $conn $tx2 ("INSERT INTO " + $tabelaHistorico + " (bd_key, bd_ano, bd_n_encomenda, bd_cliente, bd_plano_corte, operacao, maquina, responsavel, tempo_gasto_minutos, percentagem_feita, comentarios, data_registo) " +
        "VALUES (@k, @bd_ano, @n_enc, @cliente, @plano, 'escritorio', N'', @resp, 0, 0, @coment, GETDATE())")
      Add-Texto $c '@k' 255 $p.espelho.bd_key
      Add-Texto $c '@bd_ano' 50 $p.espelho.bd_ano
      Add-Texto $c '@n_enc' 100 $p.espelho.bd_n_encomenda
      Add-Texto $c '@cliente' 255 $p.espelho.bd_cliente
      Add-Texto $c '@plano' 255 $p.espelho.bd_plano_corte
      Add-Texto $c '@resp' 100 $ev.utilizador
      Add-Texto $c '@coment' 800 $ev.espelho
      [void]$c.ExecuteNonQuery()
      $espelho = $espelho + 1
    }
    $tx2.Commit()
  } catch {
    try { $tx2.Rollback() } catch { }
    $espelho = 0
    $espelhoErro = [string]$_.Exception.Message
  }
  Saida 'gravado' $libertada $espelho $espelhoErro
} finally {
  $conn.Close()
}
"""


def executar_payload(payload: dict[str, Any]) -> ResultadoEnvio:
    dados = leitura.correr_powershell(
        _PS_ESCRITA, payload, timeout=leitura.TIMEOUT_PROCESSO_S
    )
    if not isinstance(dados, dict):
        raise RuntimeError("O Streamlit não devolveu resposta ao envio.")
    resultado = str(dados.get("resultado") or "")
    if resultado not in {GRAVADO, JA_REGISTADO, CONFLITO}:
        raise RuntimeError(f"Resposta inesperada do Streamlit: {resultado or '(vazia)'}.")
    return ResultadoEnvio(
        resultado=resultado,
        libertada=bool(dados.get("libertada")),
        espelho=int(dados.get("espelho") or 0),
        espelho_erro=str(dados.get("espelho_erro") or ""),
        ensaio=bool(dados.get("ensaio")),
    )


def enviar(
    session: Session,
    avaliacao: Avaliacao,
    *,
    command_id: str,
    pasta: str = "",
    ensaio: bool = False,
) -> ResultadoEnvio:
    """Avançar no Streamlit o modelo/versão avaliado. Só com o interruptor ON.

    ``ensaio=True`` corre a transação toda e desfaz no fim: prova a ligação,
    as permissões e o SQL sem deixar nada gravado.
    """
    assert_escrita_ativa(session)
    payload = construir_payload(
        leitura.ligacao(session),
        avaliacao,
        command_id=command_id,
        versao_programa=VERSAO_APLICACAO,
        posto=socket.gethostname(),
        pasta=pasta,
        ensaio=ensaio,
    )
    return executar_payload(payload)


def explicar_erro_escrita(exc: BaseException) -> str:
    """Mensagem curta, sem detalhe técnico nem segredos."""
    normal = str(exc or "").casefold()
    if "permission was denied" in normal:
        return (
            "O SQL Server recusou a escrita: a conta configurada não tem permissão "
            "em dbo.Escritorio_Versoes / dbo.Escritorio_Eventos."
        )
    if "would be truncated" in normal:
        return "Um dos valores é maior do que a coluna do Streamlit permite."
    if "libertacao automatica" in normal:
        return "A libertação automática (material só do cliente) falhou: nada foi gravado."
    return leitura.explicar_erro_leitura(exc)
