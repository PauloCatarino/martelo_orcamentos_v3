<#
.SYNOPSIS
    Extrai as Drawing Views de uma encomenda do iMos para DXF (uma por vista), sem abrir o iX CAD.

.DESCRIPTION
    Copia o DWG da encomenda (nunca lhe mexe) e, para cada vista (camadas imosSectGround.N,
    imosSectView.N, imosSect.X), congela as outras camadas e faz -WBLOCK de tudo o que fica
    visivel: o bloco da vista + as cotas (.AutoDims) + as etiquetas (.Label), que o iMos poe
    no espaco modelo FORA do bloco da vista. Depois grava cada uma em DXF.

    Usado para conferir o resultado dos principios DV_* (desenhar com ver_vistas.py).

.EXAMPLE
    .\extrair_vistas.ps1 -Encomenda ORC_260881_2604023 -Saida C:\temp\dv_t1
    .\extrair_vistas.ps1 -Encomenda ORC_260881_2604023 -Saida C:\temp\dv_t1 -Vistas imosSectView.2
#>
param(
    [Parameter(Mandatory)][string]$Encomenda,
    [Parameter(Mandatory)][string]$Saida,
    [string[]]$Vistas,
    [string]$PastaEncomendas = 'I:\Factory\Imorder'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\imos_ferragens\_consola.ps1')

New-Item -ItemType Directory -Force $Saida | Out-Null
$origem = Join-Path $PastaEncomendas "$Encomenda\$Encomenda.DWG"
$copia = Join-Path $Saida 'obra.dwg'
Copy-Item $origem $copia -Force
"Copia de $origem ($((Get-Item $origem).LastWriteTime))"
$ini = Get-InicioScript

if (-not $Vistas) {
    # as vistas que existem = blocos imosSect* (as camadas ficam de tentativas antigas)
    $t = Invoke-ConsolaIxCad -Dwg $copia -Linhas ($ini + @('-BLOCK', '?', 'imosSect*')) -Log (Join-Path $Saida 'blocos.log') -TimeoutSec 240
    $Vistas = [regex]::Matches($t, '"(imosSect(?:Ground|View|SideView|TopView)?\.[^"]+)"') |
        ForEach-Object { $_.Groups[1].Value } | Where-Object { $_ -notmatch '^imosSectRef' } | Sort-Object -Unique
}
foreach ($v in $Vistas) {
    $dwg = Join-Path $Saida "vista_$v.dwg"
    $L = $ini + @('-LAYER', '_S', $v, '_F', '*', '_T', "$v*", '', '-WBLOCK', $dwg, '', '_NON', '0,0', '_ALL', '')
    Invoke-ConsolaIxCad -Dwg $copia -Linhas $L -Log (Join-Path $Saida "wb_$v.log") -TimeoutSec 300 | Out-Null
    if (-not (Test-Path $dwg)) { Write-Warning "Nao extraiu $v"; continue }
    Invoke-ConsolaIxCad -Dwg $dwg -Linhas ($ini + @('_.SAVEAS', '_DXF', '16', (Join-Path $Saida "vista_$v.dxf"))) -Log (Join-Path $Saida "dxf_$v.log") -TimeoutSec 200 | Out-Null
    "Extraida: $v"
}
