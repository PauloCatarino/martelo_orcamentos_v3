<#
.SYNOPSIS
    Copia o DWG e a imagem de uma ferragem para a biblioteca do iMos.

.DESCRIPTION
    I:\Library\ConnDWG          <- <Nome>.DWG  (o "Nome do desenho" da Uniao)
    I:\Library\Info\BITMAPS     <- <Nome>.jpg  (a "Preview Image" na lista de ferragens)

    Confere antes: nomes livres (o I: e' uma pasta de rede SEM Reciclagem -- nunca
    se grava por cima), DWG em formato 2018 (AC1032, como o resto da biblioteca),
    imagem 256x256. Depois de copiar, compara o hash com o original.
    A configuracao da Uniao no iMos faz-se a mao (e' o Paulo que a faz).

.EXAMPLE
    .\instalar_na_biblioteca.ps1 -Dwg C:\Temp\final_DIR.dwg -Imagem C:\Temp\DIR.jpg -Nome EMUCA_4030705_NIVELADOR_LEVEL_UP_DIR

.EXAMPLE
    # So ver o que ia fazer
    .\instalar_na_biblioteca.ps1 -Dwg ... -Imagem ... -Nome ... -Simular
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Dwg,
    [Parameter(Mandatory)][string]$Imagem,
    [Parameter(Mandatory)][string]$Nome,
    [string]$PastaDwg = 'I:\Library\ConnDWG',
    [string]$PastaImagens = 'I:\Library\Info\BITMAPS',
    [switch]$Simular
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\_consola.ps1"

$Dwg = (Resolve-Path $Dwg).Path
$Imagem = (Resolve-Path $Imagem).Path
$destDwg = Join-Path $PastaDwg "$Nome.DWG"
$destImg = Join-Path $PastaImagens "$Nome.jpg"
Assert-NaoExiste @($destDwg, $destImg)

$cab = New-Object byte[] 6
$f = [IO.File]::OpenRead($Dwg); [void]$f.Read($cab, 0, 6); $f.Close()
$versao = [Text.Encoding]::ASCII.GetString($cab)
if ($versao -ne 'AC1032') { Write-Warning "O DWG esta em $versao (a biblioteca usa AC1032 = 2018)." }
Add-Type -AssemblyName System.Drawing
$im = [System.Drawing.Image]::FromFile($Imagem)
$dim = "$($im.Width)x$($im.Height)"
$im.Dispose()
if ($dim -ne '256x256') { Write-Warning "A imagem tem $dim (as da biblioteca tem 256x256)." }

Write-Host "DWG    : $Dwg -> $destDwg ($versao)"
Write-Host "Imagem : $Imagem -> $destImg ($dim)"
if ($Simular) { Write-Host 'Simulacao: nada copiado.'; return }
foreach ($par in @(@($Dwg, $destDwg), @($Imagem, $destImg))) {
    Copy-Item -LiteralPath $par[0] -Destination $par[1]
    $ok = (Get-FileHash $par[0]).Hash -eq (Get-FileHash $par[1]).Hash
    Write-Host ("{0}  {1} bytes  {2}" -f $par[1], (Get-Item $par[1]).Length, $(if ($ok) { 'confere' } else { 'HASH DIFERENTE' }))
    if (-not $ok) { throw "A copia de $($par[1]) nao confere com o original." }
}
