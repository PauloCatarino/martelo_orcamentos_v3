<#
.SYNOPSIS
    Converte o STEP do fabricante num DWG com os solidos soltos, mais o SAT para medir.

.DESCRIPTION
    1. AcTranslators (do iX CAD) converte o STEP -> <Nome>_bruto.dwg. Vem com blocos
       dentro de blocos, um solido por camada (1, 2, 3...) e numa posicao qualquer.
    2. Explode os blocos ate nao sobrar nenhum, por passagens: cada passagem conta os
       blocos (LIST) e faz exatamente esse numero de EXPLODE, com as camadas dos
       solidos congeladas -- o EXPLODE da consola desfaz um objeto de cada vez e, se
       apanhasse um solido, desfazia-o em bocados.
    3. Grava <Nome>_limpo.dwg (-WBLOCK *, que faz de PURGE), <Nome>.sat (ACISOUT) e
       <Nome>_entidades.txt com uma linha por entidade (tipo, camada, caixa).

    Depois: medir com  python -m scripts.imos_ferragens.sat corpos <Nome>.sat
    e ver em arame com  arestas.ps1  +  python -m scripts.imos_ferragens.arame.

    SURFACE no resultado = peca que o tradutor nao conseguiu fechar em solido
    (aconteceu com a lingueta do nivelador LevelUp): nao entra numa UNION nem se
    converte (nao ha SURFSCULPT); refaz-se com primitivas na montagem.

.EXAMPLE
    .\step_para_dwg.ps1 -Step C:\Users\Utilizador\Downloads\40307.step -Pasta C:\Temp\nivelador
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Step,
    # Pasta de trabalho (criada se nao existir). Vazio = %TEMP%\imos_ferragens\<Nome>
    [string]$Pasta = '',
    # Nome base dos ficheiros. Vazio = nome do STEP.
    [string]$Nome = '',
    [int]$MaxPassagens = 12,
    [int]$TimeoutSec = 600
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_consola.ps1"

$Step = (Resolve-Path $Step).Path
if (-not $Nome) { $Nome = [IO.Path]::GetFileNameWithoutExtension($Step) }
if (-not $Pasta) { $Pasta = Join-Path $env:TEMP "imos_ferragens\$Nome" }
New-Item -ItemType Directory -Force $Pasta | Out-Null
$bruto = Join-Path $Pasta "${Nome}_bruto.dwg"
$limpo = Join-Path $Pasta "${Nome}_limpo.dwg"
$sat = Join-Path $Pasta "$Nome.sat"
$resumo = Join-Path $Pasta "${Nome}_entidades.txt"
Assert-NaoExiste @($bruto, $limpo, $sat, $resumo)

# 1) STEP -> DWG
Write-Host "[1/3] A converter $Step"
$tradutor = Join-Path (Get-KernelIxCad) 'AcTranslators.exe'
$p = Start-Process -FilePath $tradutor -NoNewWindow -PassThru `
    -ArgumentList @('-i', "`"$Step`"", '-o', "`"$bruto`"", '-Product', 'ACAD', '-Language', 'en-US') `
    -RedirectStandardOutput (Join-Path $Pasta "${Nome}_tradutor.log")
if (-not $p.WaitForExit($TimeoutSec * 1000)) { $p.Kill(); throw 'O AcTranslators nao acabou a tempo.' }
if (-not (Test-Path $bruto)) { throw "O AcTranslators nao criou $bruto (ver ${Nome}_tradutor.log)" }

function Get-Entidades([string]$Dwg, [string]$Log) {
    $t = Invoke-ConsolaIxCad -Dwg $Dwg -Linhas ((Get-InicioScript) + @('-LAYER', '_T', '*', '', '_.LIST', '_ALL', '')) -Log $Log -TimeoutSec $TimeoutSec
    ConvertFrom-ListaConsola $t
}

# 2) explodir por passagens
$atual = $bruto
$ents = Get-Entidades $atual (Join-Path $Pasta "${Nome}_lista_0.log")
for ($n = 1; $n -le $MaxPassagens; $n++) {
    $blocos = @($ents | Where-Object Tipo -eq 'BLOCK REFERENCE')
    if ($blocos.Count -eq 0) { break }
    $camadasSolidas = @($ents | Where-Object { $_.Tipo -ne 'BLOCK REFERENCE' } | ForEach-Object Camada | Sort-Object -Unique)
    $mistas = @($blocos | Where-Object { $camadasSolidas -contains $_.Camada })
    if ($mistas.Count) {
        throw ("Ha blocos na mesma camada que solidos/superficies ({0}): explodir assim desfazia os solidos. Tratar a mao." -f (($mistas | ForEach-Object Camada | Sort-Object -Unique) -join ','))
    }
    Write-Host ("[2/3] Passagem {0}: {1} bloco(s) a explodir" -f $n, $blocos.Count)
    $L = Get-InicioScript
    $L += @('-LAYER', '_T', '*', '_S', ($blocos[0].Camada), '')
    if ($camadasSolidas.Count) { $L += @('-LAYER', '_F', ($camadasSolidas -join ','), '') }
    foreach ($b in $blocos) { $L += @('_.EXPLODE', '_ALL') }
    $seguinte = Join-Path $Pasta ("{0}_explodido_{1}.dwg" -f $Nome, $n)
    Assert-NaoExiste @($seguinte)
    $L += @('-LAYER', '_T', '*', '', '_.SAVEAS', '2018', $seguinte)
    Invoke-ConsolaIxCad -Dwg $atual -Linhas $L -Log (Join-Path $Pasta "${Nome}_explodir_$n.log") -TimeoutSec $TimeoutSec | Out-Null
    if (-not (Test-Path $seguinte)) { throw "A passagem $n nao gravou $seguinte (ver ${Nome}_explodir_$n.log)" }
    $antes = $blocos.Count
    $atual = $seguinte
    $ents = Get-Entidades $atual (Join-Path $Pasta "${Nome}_lista_$n.log")
    $depois = @($ents | Where-Object Tipo -eq 'BLOCK REFERENCE').Count
    $estranhos = @($ents | Where-Object { $_.Tipo -in @('REGION', 'BODY') })
    if ($estranhos.Count) { throw 'Apareceram REGION/BODY: um solido foi desfeito pelo EXPLODE. Ver os registos.' }
    if ($depois -ge $antes -and $n -gt 1 -and $depois -gt 0) {
        Write-Warning "A passagem $n nao reduziu os blocos ($antes -> $depois). Parar e ver a mao."
        break
    }
}

# 3) limpo + SAT + resumo
Write-Host '[3/3] A gravar o DWG limpo e o SAT'
$L = (Get-InicioScript) + @('-WBLOCK', $limpo, '*', 'ACISOUT', '_ALL', '', $sat)
Invoke-ConsolaIxCad -Dwg $atual -Linhas $L -Log (Join-Path $Pasta "${Nome}_limpo.log") -TimeoutSec $TimeoutSec | Out-Null
$ents = Get-Entidades $limpo (Join-Path $Pasta "${Nome}_lista_final.log")
$linhas = $ents | ForEach-Object {
    $mn = if ($_.Min) { Format-Ponto $_.Min } else { '' }
    $mx = if ($_.Max) { Format-Ponto $_.Max } else { '' }
    '{0,-16} camada {1,-6} min {2,-28} max {3}' -f $_.Tipo, $_.Camada, $mn, $mx
}
$linhas | Set-Content -Encoding utf8 $resumo
$linhas | ForEach-Object { Write-Host $_ }
if (@($ents | Where-Object Tipo -eq 'SURFACE').Count) {
    Write-Warning 'Ha SURFACE: o tradutor nao fechou essa peca em solido. Refazer com primitivas na montagem.'
}
Write-Host "DWG limpo: $limpo"
Write-Host "SAT:       $sat"
