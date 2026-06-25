"""Geração do Excel 'Lista Material_IMOS' (template .xltm via Excel COM)."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.producao import Producao
from app.services.system_setting_service import SystemSettingService

KEY_PASTA_BASE_DADOS_ORCAMENTO = "pasta_base_dados_orcamento"
TEMPLATE_FILENAME = "Lista_Material_IMOS_MARTELO.xltm"


@dataclass(frozen=True)
class ListaMaterialImosContext:
    processo_id: int
    folder_path: Path
    template_path: Path
    output_path: Path
    values_b64: str


def prepare_lista_material_imos(
    session: Session,
    *,
    processo_id: int,
    nome_enc_imos: str,
    values: dict,
) -> ListaMaterialImosContext:
    processo = session.get(Producao, int(processo_id))
    if processo is None:
        raise ValueError("Processo de producao nao encontrado.")

    pasta_txt = str(getattr(processo, "pasta_servidor", "") or "").strip()
    if not pasta_txt:
        raise ValueError(
            "Pasta do processo em falta.\n\n"
            "Crie a pasta do processo (Novo Processo / Nova Versao) antes de gerar a Lista Material."
        )
    folder_path = Path(pasta_txt)
    if not folder_path.exists() or not folder_path.is_dir():
        raise ValueError(f"Pasta do processo nao encontrada:\n{folder_path}")

    nome_enc_txt = str(nome_enc_imos or "").strip()
    if not nome_enc_txt:
        raise ValueError("Nome Enc IMOS IX em falta.")

    base_txt = (
        SystemSettingService(session).obter_valor(KEY_PASTA_BASE_DADOS_ORCAMENTO, "") or ""
    ).strip()
    if not base_txt:
        raise ValueError(
            "Modelo Excel nao encontrado: a setting 'Pasta Base Dados Orcamento' "
            "nao esta configurada em Caminhos do Sistema."
        )
    template_path = Path(base_txt) / TEMPLATE_FILENAME
    if not template_path.is_file():
        raise ValueError(f"Modelo Excel nao encontrado:\n{template_path}")

    output_path = folder_path / f"Lista_Material_{nome_enc_txt}.xlsm"
    values_json = json.dumps(dict(values or {}), ensure_ascii=False)
    values_b64 = base64.b64encode(values_json.encode("utf-8")).decode("ascii")

    return ListaMaterialImosContext(
        processo_id=int(processo_id),
        folder_path=folder_path,
        template_path=template_path,
        output_path=output_path,
        values_b64=values_b64,
    )


def execute_lista_material_imos(
    context: ListaMaterialImosContext, *, timeout_seconds: int = 240
) -> Path:
    temp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", suffix=".ps1", delete=False
        ) as tf:
            tf.write(_lista_material_imos_ps_script())
            temp_path = tf.name

        cmd = [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-STA",
            "-File",
            temp_path,
            str(context.template_path),
            str(context.output_path),
            context.values_b64,
        ]
        creationflags = (
            getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        )
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
            creationflags=creationflags,
        )
        if result.returncode != 0:
            stdout = (result.stdout or "").strip()
            stderr = (result.stderr or "").strip()
            detail = "\n".join(s for s in (stderr, stdout) if s)
            raise RuntimeError(detail or f"Codigo de saida: {result.returncode}")
        return context.output_path
    finally:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass


def _lista_material_imos_ps_script() -> str:
    return r"""
param(
  [Parameter(Mandatory=$true)][string]$TemplatePath,
  [Parameter(Mandatory=$true)][string]$OutputPath,
  [Parameter(Mandatory=$true)][string]$ValuesB64
)
$ErrorActionPreference = 'Stop'

$valuesJson = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($ValuesB64))
$v = $valuesJson | ConvertFrom-Json

function To-OADate([string]$text) {
  if (-not $text) { return $null }
  try {
    $dt = [datetime]::ParseExact($text, 'dd-MM-yyyy', $null)
    return $dt.ToOADate()
  } catch { return $null }
}

$excel = New-Object -ComObject Excel.Application
$excel.Visible = $false
$excel.DisplayAlerts = $false
try { $excel.AutomationSecurity = 3 } catch { }

try {
  $m = [Type]::Missing
  $args = @($TemplatePath, 0, $true, $m, $m, $m, $m, $m, $m, $m, $m, $m, $m, $m, 1)
  $wb = $excel.Workbooks.GetType().InvokeMember('Open', [System.Reflection.BindingFlags]::InvokeMethod, $null, $excel.Workbooks, $args)
  try {
    $ws = $null
    foreach ($sn in @('DEFENICOES','DEFINICOES')) {
      try { $ws = $wb.Worksheets.Item($sn); break } catch { }
    }
    if ($ws -eq $null) { $ws = $wb.Worksheets.Item(1) }

    $ws.Range('B3').Value2 = [string]$v.RESPONSAVEL
    $ws.Range('C3').Value2 = [string]$v.REF_CLIENTE
    $ws.Range('D3').Value2 = [string]$v.OBRA
    $ws.Range('E3').Value2 = [string]$v.NOME_ENC_IMOS_IX
    $ws.Range('F3').Value2 = [string]$v.NUM_CLIENTE_PHC
    $ws.Range('G3').Value2 = [string]$v.NOME_CLIENTE
    $ws.Range('H3').Value2 = [string]$v.NOME_CLIENTE_SIMPLEX
    $ws.Range('I3').Value2 = [string]$v.LOCALIZACAO
    $desc = [string]$v.DESCRICAO_PRODUCAO
    if ($desc -eq '') { $desc = [string]$v.DESCRICAO_ARTIGOS }
    $ws.Range('J3').Value2 = $desc
    $ws.Range('K3').Value2 = [string]$v.MATERIAIS

    $qtd = $null
    if ($v.QTD -ne $null -and [string]$v.QTD -ne '') { try { $qtd = [string]([double]([string]$v.QTD).Replace(',', '.')) } catch { $qtd = [string]$v.QTD } }
    $ws.Range('L3').Value2 = if ($qtd -eq $null) { '' } else { $qtd }

    $ws.Range('M3').Value2 = [string]$v.PLANO_CORTE

    $dtEnd = To-OADate ([string]$v.DATA_CONCLUSAO)
    $dtIni = To-OADate ([string]$v.DATA_INICIO)
    $ws.Range('N3').Value2 = if ($dtEnd -eq $null) { '' } else { [string]$dtEnd }
    $ws.Range('O3').Value2 = if ($dtIni -eq $null) { '' } else { [string]$dtIni }
    try { $ws.Range('N3').NumberFormatLocal = 'dd-mm-aaaa' } catch { $ws.Range('N3').NumberFormat = 'dd-mm-yyyy' }
    try { $ws.Range('O3').NumberFormatLocal = 'dd-mm-aaaa' } catch { $ws.Range('O3').NumberFormat = 'dd-mm-yyyy' }

    $ws.Range('P3').Value2 = [string]$v.ENC_PHC

    if (Test-Path -LiteralPath $OutputPath) { Remove-Item -LiteralPath $OutputPath -Force }
    $wb.SaveAs($OutputPath, 52)

    try {
      $wsCut = $wb.Worksheets.Item('LISTAGEM_CUT_RITE')
      $lo = $wsCut.ListObjects.Item('Tabela_Cut_Rite')
      $rangeAddr = $lo.Range.Address(0,0)
      $styleName = $lo.TableStyle
      $formulas = @{}
      for ($i = 1; $i -le $lo.ListColumns.Count; $i++) {
        $col = $lo.ListColumns.Item($i)
        $colName = [string]$col.Name
        $f = $null
        try {
          if ($col.DataBodyRange -ne $null) {
            $val = $col.DataBodyRange.Formula
            if ($val -is [System.Array]) { $f = $val.GetValue(1,1) } else { $f = $val }
          }
        } catch { }
        if ($f -ne $null -and [string]$f -ne '') { $formulas[$colName] = [string]$f }
        [Runtime.InteropServices.Marshal]::ReleaseComObject($col) | Out-Null
      }

      $lo.Unlist() | Out-Null
      [Runtime.InteropServices.Marshal]::ReleaseComObject($lo) | Out-Null

      $newLo = $wsCut.ListObjects.Add(1, $wsCut.Range($rangeAddr), $null, 1)
      $newLo.Name = 'Tabela_Cut_Rite'
      try { $newLo.TableStyle = $styleName } catch { }

      foreach ($k in $formulas.Keys) {
        try {
          $c = $newLo.ListColumns.Item($k)
          if ($c.DataBodyRange -ne $null) { $c.DataBodyRange.Formula = $formulas[$k] }
          [Runtime.InteropServices.Marshal]::ReleaseComObject($c) | Out-Null
        } catch { }
      }
      [Runtime.InteropServices.Marshal]::ReleaseComObject($newLo) | Out-Null
      [Runtime.InteropServices.Marshal]::ReleaseComObject($wsCut) | Out-Null

      $wb.Save() | Out-Null
    } catch { }
  } finally {
    $wb.Close($false) | Out-Null
    [Runtime.InteropServices.Marshal]::ReleaseComObject($wb) | Out-Null
  }
} finally {
  $excel.Quit() | Out-Null
  [Runtime.InteropServices.Marshal]::ReleaseComObject($excel) | Out-Null
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}
"""
