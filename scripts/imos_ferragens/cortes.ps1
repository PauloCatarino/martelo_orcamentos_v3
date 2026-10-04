<#
.SYNOPSIS
    Corta os solidos de um DWG com planos horizontais e grava as regioes em DXF R12.

.DESCRIPTION
    E' a forma de "ver" uma peca sem CAD grafico: a consola corta (SECTION) de Z em Z,
    o DXF R12 guarda cada regiao como um bloco de linhas/arcos, e o Python
    (scripts.imos_ferragens.vistas / imagem / sobrepor) refaz o volume e desenha.
    Grava tambem <Dxf>.json com o primeiro corte e o passo.

    O DWG deve ter so solidos (de preferencia ja montado num so). Passo 0.25 mm
    chega para conferir; para a imagem final usar 0.15 mm. Por omissao corta a
    altura toda da peca (le a caixa com LIST).

.EXAMPLE
    .\cortes.ps1 -Dwg C:\Temp\nivelador\final_DIR.dwg -Dxf C:\Temp\nivelador\cortes_DIR.dxf -Passo 0.15
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Dwg,
    [Parameter(Mandatory)][string]$Dxf,
    [double]$Passo = 0.25,
    # Limites em Z; vazios = caixa da peca (com meio passo de folga para dentro)
    [Nullable[double]]$De = $null,
    [Nullable[double]]$Ate = $null,
    [int]$TimeoutSec = 2400
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_consola.ps1"

$Dwg = (Resolve-Path $Dwg).Path
$Dxf = [IO.Path]::GetFullPath($Dxf)
Assert-NaoExiste @($Dxf, "$Dxf.json")
$pasta = Split-Path $Dxf

if ($null -eq $De -or $null -eq $Ate) {
    $t = Invoke-ConsolaIxCad -Dwg $Dwg -Linhas ((Get-InicioScript) + @('_.LIST', '_ALL', '')) `
        -Log (Join-Path $pasta ([IO.Path]::GetFileName($Dxf) + '.caixa.log'))
    $ents = @(ConvertFrom-ListaConsola $t | Where-Object { $_.Min })
    if (-not $ents.Count) { throw 'Nao encontrei solidos no DWG.' }
    if ($null -eq $De) { $De = ($ents | ForEach-Object { $_.Min[2] } | Measure-Object -Minimum).Minimum + $Passo / 2 }
    if ($null -eq $Ate) { $Ate = ($ents | ForEach-Object { $_.Max[2] } | Measure-Object -Maximum).Maximum - $Passo / 2 }
}
$n = [int][Math]::Floor(($Ate - $De) / $Passo + 1e-9)
$ci = [Globalization.CultureInfo]::InvariantCulture
Write-Host ([string]::Format($ci, '{0} cortes de Z={1:0.###} a Z={2:0.###} (passo {3})', ($n + 1), $De, ($De + $n * $Passo), $Passo))

$L = (Get-InicioScript) + @('-LAYER', '_M', 'CORTES', '')
for ($i = 0; $i -le $n; $i++) {
    # 1.o corte apanha todos os solidos; os seguintes usam a selecao anterior (_P),
    # senao as regioes ja feitas tambem entravam na selecao
    $sel = if ($i -eq 0) { '_ALL' } else { '_P' }
    $L += @('_.SECTION', $sel, '', '_XY', '_NON', (Format-Ponto 0, 0, ($De + $i * $Passo)))
}
# deixar so as regioes: congelar CORTES (nao pode ser a camada atual) e apagar o resto
$L += @('-LAYER', '_S', '0', '_F', 'CORTES', '', '_.ERASE', '_ALL', '', '-LAYER', '_T', '*', '')
$L += @('_.SAVEAS', '_DXF', '_V', '_R12', '16', $Dxf)
$texto = Invoke-ConsolaIxCad -Dwg $Dwg -Linhas $L -Log "$Dxf.log" -TimeoutSec $TimeoutSec
if (-not (Test-Path $Dxf)) { throw "Nao foi gravado $Dxf (ver $Dxf.log)" }
# o kernel falha o SECTION em solidos com defeitos ("Modeling Operation Error");
# o volume preenche esses cortes com o vizinho, mas convem saber que aconteceu
$falhados = ([regex]::Matches($texto, 'SECTION failed')).Count
if ($falhados) { Write-Warning "$falhados corte(s) falharam no kernel (solido com defeitos?). Ver $Dxf.log" }
('{{"de": {0}, "passo": {1}, "cortes": {2}, "falhados": {3}}}' -f $De.ToString($ci), $Passo.ToString($ci), ($n + 1), $falhados) |
    Set-Content -Encoding ascii "$Dxf.json"
Write-Host "Gravado $Dxf"
