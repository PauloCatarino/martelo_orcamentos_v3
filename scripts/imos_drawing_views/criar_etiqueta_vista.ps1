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

    Com -Simples (pedido do Paulo, 06-10): so o nome da vista ("Vista 1"), sem circulo, linha,
    numero nem escala, encostado ao desenho (ver o etiqueta_vista_dxf.py).

.EXAMPLE
    .\criar_etiqueta_vista.ps1 -Saida C:\temp\dv_etiqueta_vista
    .\criar_etiqueta_vista.ps1 -Saida C:\temp\dv_etiqueta_simples -Simples
#>
param(
    [Parameter(Mandatory)][string]$Saida,
    [string]$Origem = (Join-Path $env:APPDATA 'imos AG\iX CAD 2025\config\DrawingFlags'),
    [switch]$Simples
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
    $modo = @()
    if ($Simples) { $modo = @(if ($n -eq 'imosLabelElevation') { 'alcado' } else { 'planta' }) }
    & $py (Join-Path $PSScriptRoot 'etiqueta_vista_dxf.py') $dxf $novo @modo
    if ($LASTEXITCODE) { throw "etiqueta_vista_dxf.py falhou ($n)" }
    $pontos = @()
    if ($Simples) {
        # R9 (06-10, APAGAR_16): so com o atributo, o bloco nao tem extensao e o iMos inseria-o
        # em (1E20,1E20): o Zoom extents das folhas ia ate la e o PDF saia vazio. Dois pontos
        # na camada Defpoints (nao imprime) nos cantos do simbolo com circulo (-69.25,-26.25 a
        # -20,-3.75), com que o iMos o punha a -80,-96.25 do canto da vista (APAGAR_14 e 15).
        # R10 (APAGAR_17): o Zoom extents conta com os pontos, e 69 mm a esquerda deixavam a
        # folha com espaco vazio e o desenho mais pequeno. Passam para a volta do texto
        # "Vista 1" (3 mm de altura, ~19 mm de largura; ver SIMPLES no etiqueta_vista_dxf.py).
        # R11: o do alcado desceu (texto de 1,5 a 4,5).
        $cantos = if ($n -eq 'imosLabelElevation') { @('-20,1.5', '-1,4.5') } else { @('5,-4', '24,-1') }
        $pontos = @('-LAYER', '_M', 'Defpoints', '_P', '_N', 'Defpoints', '',
            '_.POINT', '_NON', $cantos[0], '_.POINT', '_NON', $cantos[1], '-LAYER', '_S', '0', '')
    }
    Invoke-ConsolaIxCad -Dwg $novo -Linhas ((Get-InicioScript) + $pontos + @('_.ZOOM', '_E', '_.SAVEAS', '2018', $final)) -Log (Join-Path $Saida "$n.passo2.log") -TimeoutSec 120 | Out-Null
    if (-not (Test-Path $final)) { throw "Nao gravou $final" }
    "Criado: $final"
}
