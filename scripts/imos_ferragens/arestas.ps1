<#
.SYNOPSIS
    Extrai as arestas dos solidos (XEDGES) para um DXF, para ver a peca em arame.

.DESCRIPTION
    Sem -Camadas: todas as arestas na camada ARESTAS.
    Com -Camadas "3,10,16": as arestas de cada camada (= cada peca, no DWG que sai
    do step_para_dwg) ficam na camada com o mesmo nome, para as ver a cores:

        python -m scripts.imos_ferragens.arame <Dxf> --saida arame.png --camadas 3,10,16

    Cada camada pedida TEM de ter alguma coisa: uma selecao vazia encrava a consola.

.EXAMPLE
    .\arestas.ps1 -Dwg C:\Temp\nivelador\40307_limpo.dwg -Dxf C:\Temp\nivelador\arestas.dxf -Camadas 3,10,16
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Dwg,
    [Parameter(Mandatory)][string]$Dxf,
    # -Camadas 3,10,16 (lista) ou "3,10,16" (texto)
    [string[]]$Camadas = @(),
    [int]$TimeoutSec = 600
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_consola.ps1"

$Dwg = (Resolve-Path $Dwg).Path
$Dxf = [IO.Path]::GetFullPath($Dxf)
Assert-NaoExiste @($Dxf)
$L = Get-InicioScript
$lista = @($Camadas | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
if ($lista.Count) {
    foreach ($c in $lista) {
        # camada atual = a da peca; congelar todas as outras (a atual nao congela)
        $L += @('-LAYER', '_T', '*', '_S', $c, '_F', '*', '', 'XEDGES', '_ALL', '')
    }
} else {
    $L += @('-LAYER', '_M', 'ARESTAS', '', 'XEDGES', '_ALL', '')
}
$L += @('-LAYER', '_T', '*', '', '_.SAVEAS', '_DXF', '16', $Dxf)
Invoke-ConsolaIxCad -Dwg $Dwg -Linhas $L -Log "$Dxf.log" -TimeoutSec $TimeoutSec | Out-Null
if (-not (Test-Path $Dxf)) { throw "Nao foi gravado $Dxf (ver $Dxf.log)" }
Write-Host "Gravado $Dxf"
