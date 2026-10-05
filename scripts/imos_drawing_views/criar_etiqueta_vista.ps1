<#
.SYNOPSIS
    Cria versoes novas do simbolo de nome das vistas (circulo + "Vista 1" + escala).

.DESCRIPTION
    Le os blocos imosLabelElevation.dwg e imosLabelPlanview.dwg da pasta DrawingFlags do
    iX CAD, passa-os a DXF na consola, muda as medidas com o etiqueta_vista_dxf.py (ver la
    o que muda) e volta a DWG. Os ficheiros novos ficam em -Saida, com o mesmo nome.

    NAO instala: a pasta DrawingFlags e' configuracao do iX CAD. Para os usar, o Paulo
    guarda os originais e copia estes por cima (pedido explicito dele). As obras que ja tem
    o bloco definido continuam com o antigo; as obras novas usam o novo.

.EXAMPLE
    .\criar_etiqueta_vista.ps1 -Saida C:\temp\dv_etiqueta_vista
#>
param(
    [Parameter(Mandatory)][string]$Saida,
    [string]$Origem = (Join-Path $env:APPDATA 'imos AG\iX CAD 2025\config\DrawingFlags')
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\imos_ferragens\_consola.ps1')

New-Item -ItemType Directory -Force $Saida | Out-Null
$py = Get-PythonMartelo
foreach ($n in 'imosLabelElevation', 'imosLabelPlanview') {
    $final = Join-Path $Saida "$n.dwg"
    Assert-NaoExiste $final
    $copia = Join-Path $Saida "$n.original.dwg"
    Copy-Item (Join-Path $Origem "$n.dwg") $copia -Force
    $dxf = Join-Path $Saida "$n.original.dxf"
    $novo = Join-Path $Saida "$n.novo.dxf"
    Invoke-ConsolaIxCad -Dwg $copia -Linhas ((Get-InicioScript) + @('_.SAVEAS', '_DXF', '16', $dxf)) -Log (Join-Path $Saida "$n.passo1.log") -TimeoutSec 120 | Out-Null
    & $py (Join-Path $PSScriptRoot 'etiqueta_vista_dxf.py') $dxf $novo
    if ($LASTEXITCODE) { throw "etiqueta_vista_dxf.py falhou ($n)" }
    Invoke-ConsolaIxCad -Dwg $novo -Linhas ((Get-InicioScript) + @('_.ZOOM', '_E', '_.SAVEAS', '2018', $final)) -Log (Join-Path $Saida "$n.passo2.log") -TimeoutSec 120 | Out-Null
    if (-not (Test-Path $final)) { throw "Nao gravou $final" }
    "Criado: $final"
}
