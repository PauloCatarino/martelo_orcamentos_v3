<#
.SYNOPSIS
    EXEMPLO de montagem: nivelador Emuca LevelUp 1 (4030705 direito / 4030805 esquerdo).

.DESCRIPTION
    Feito a 2026-10-04 para separar a uniao NIVELADOR_40086 em direito/esquerdo.
    Serve de modelo para a montagem de outras ferragens: copiar, trocar as medidas.
    Todas as medidas vieram do SAT (scripts.imos_ferragens.sat) e da ficha da Emuca.

    Entrada: o <nome>_limpo.dwg do step_para_dwg.ps1 (STEP 40307 = direito,
    40308 = esquerdo). Os numeros das camadas sao os que o tradutor deu a estes
    STEP; outro STEP tera outros.

    O que faz, por esta ordem (a mesma receita serve para quase tudo):
      1. apaga a SURFACE que o tradutor nao fechou (a lingueta anti-queda);
      2. SLICE: corta as cavilhas nervuradas rente a face de apoio;
      3. SUBTRACT: tira os encaixes das cavilhas (faces spline, pesadas);
      4. troca os dois excentricos (muitas splines) por cilindros;
      5. cria pinos lisos com chanfro no lugar das cavilhas;
      6. refaz a lingueta com primitivas (barra, nervuras, placa, berco);
      7. UNION -> um so solido; MOVE + ROTATE3D para o referencial da uniao;
      8. camada 0, cor zincado; -WBLOCK * para um DWG limpo (faz de PURGE).

    Referencial (o do desenho antigo GS_SH_6301 que a uniao ja usava): origem na
    ponta da cavilha de cima, cavilhas segundo +X (direito) / -X (esquerdo),
    cima = +Z, gancho/parede = +Y; cavilhas a Z 0 / -32 / -64.
    O STEP da Emuca vem com Z ao contrario, cavilhas segundo Y: a rotacao de 180
    graus em torno do eixo (1,1,0) faz (x, y, z) -> (y, x, -z).

    Resultado: direito 622 kB, esquerdo 574 kB (o STEP convertido tinha 2,8 MB).

.EXAMPLE
    .\nivelador_levelup.ps1 -Lado DIR -Origem C:\Temp\40307\40307_limpo.dwg -Destino C:\Temp\40307\final_DIR.dwg
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidateSet('DIR', 'ESQ')][string]$Lado,
    [Parameter(Mandatory)][string]$Origem,
    [Parameter(Mandatory)][string]$Destino,
    # Zincado. Aluminio = 161,161,160.
    [string]$Cor = '186,192,200'
)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\..\_consola.ps1"
$Origem = (Resolve-Path $Origem).Path
$Destino = [IO.Path]::GetFullPath($Destino)
Assert-NaoExiste @($Destino)
function P([double[]]$v) { Format-Ponto $v }

# ---- medidas (coordenadas do STEP, mm) ----
$zBarra = 131.46                  # eixo da barra da lingueta
$zCavilhaCima = 33.96             # no STEP a cavilha "de cima" e' a de Z menor
$xCavilhas = 10.719
$zCavilhas = 33.96, 65.96, 97.96  # passo 32
if ($Lado -eq 'DIR') {
    $xBarra = 9.719; $yPonta = 72.611; $y0 = 30.511; $y1 = 72.711
    $nervuras = 63.0, 65.25, 67.5, 69.75, 72.0
    $yPlaca = 40.84, 52.18; $yBerco = 41.04, 51.99
    $camPlaca = 12; $camExcA = 16; $camExcB = 3; $s = 1.0   # s = sentido das cavilhas em Y
    $yParafuso = 43.611
} else {
    # o esquerdo e' o espelho em Y (Y -> 64.222 - Y) com a lingueta 1 mm ao lado
    $xBarra = 10.719; $yPonta = -8.389; $y0 = -8.489; $y1 = 33.711
    $nervuras = 1.222, -1.028, -3.278, -5.528, -7.778
    $yPlaca = 12.042, 23.382; $yBerco = 12.232, 23.182
    $camPlaca = 1; $camExcA = 9; $camExcB = 6; $s = -1.0
    $yParafuso = 20.611
}
$yFace = $yPonta - $s * 12.0      # face de apoio na lateral (cavilhas saem 12 mm)

$L = New-Object System.Collections.Generic.List[string]
function A([string[]]$x) { $L.AddRange($x) }
function SoCamada([int]$c) { A '-LAYER', '_T', '*', '_S', "$c", '_F', '*', '' }

A (Get-InicioScript)
# 1) a SURFACE da lingueta e' a unica coisa na camada 0
A '-LAYER', '_S', '0', '_F', '*', '', '_.ERASE', '_ALL', ''
# 2) placa lateral: cavilhas nervuradas fora
SoCamada $camPlaca
A '_.SLICE', '_ALL', '', '_ZX', '_NON', (P 0, ($yFace + $s * 0.04), 0), '_NON', (P 10, ($yFace - $s * 20), 60)
# 3) encaixes das cavilhas (o _R _L tira a caixa acabada de fazer do 1.o conjunto)
foreach ($z in $zCavilhas) {
    A '_.BOX', '_NON', (P 11.6, ($yFace - $s * 2.5), ($z - 5.0)), '_NON', (P 14.0, ($yFace + $s * 0.7), ($z + 5.0))
    A '_.SUBTRACT', '_ALL', '_R', '_L', '', '_L', ''
}
# 4) excentricos -> cilindros
SoCamada $camExcA
A '_.ERASE', '_ALL', ''
SoCamada $camExcB
A '_.ERASE', '_ALL', ''
A '-LAYER', '_T', '*', '_S', '0', ''
A '_.CYLINDER', '_NON', (P 7.72, $yParafuso, 7.66), '5.0', '_A', '_NON', (P 15.22, $yParafuso, 7.66)
A '_.CYLINDER', '_NON', (P 4.92, $yParafuso, 38.36), '7.0', '_A', '_NON', (P 17.37, $yParafuso, 38.36)
# 5) pinos lisos D9,9 com chanfro
foreach ($z in $zCavilhas) {
    A '_.CYLINDER', '_NON', (P $xCavilhas, ($yFace - $s * 0.6), $z), '4.95', '_A', '_NON', (P $xCavilhas, ($yPonta - $s * 1.0), $z)
    A '_.CONE', '_NON', (P $xCavilhas, ($yPonta - $s * 1.0), $z), '4.95', '_T', '4.3', '_A', '_NON', (P $xCavilhas, $yPonta, $z)
}
# 6) lingueta: barra D7, 5 nervuras, placa vertical e berco
A '_.CYLINDER', '_NON', (P $xBarra, $y0, $zBarra), '3.5', '_A', '_NON', (P $xBarra, $y1, $zBarra)
foreach ($y in $nervuras) {
    A '_.CYLINDER', '_NON', (P $xBarra, ($y - 0.4), $zBarra), '4.45', '_A', '_NON', (P $xBarra, ($y + 0.4), $zBarra)
}
A '_.BOX', '_NON', (P ($xBarra - 0.7), $yPlaca[0], 96.79), '_NON', (P ($xBarra + 0.7), $yPlaca[1], 128.0)
A '_.BOX', '_NON', (P ($xBarra - 3.5), $yBerco[0], 121.85), '_NON', (P ($xBarra + 3.5), $yBerco[1], 128.0)
A '_.CYLINDER', '_NON', (P $xBarra, $yBerco[0], $zBarra), '4.5', '_A', '_NON', (P $xBarra, $yBerco[1], $zBarra)
# 7) um so solido, no referencial da uniao
A '_.UNION', '_ALL', ''
A '_.MOVE', '_ALL', '', '_NON', (P $xCavilhas, $yPonta, $zCavilhaCima), '_NON', '0,0,0'
A '_.ROTATE3D', '_ALL', '', '_NON', '0,0,0', '_NON', '1,1,0', '180'
# 8) camada 0, cor, ficheiro limpo
A '_.CHPROP', '_ALL', '', '_LA', '0', '_C', '_T', $Cor, ''
A 'INSBASE', '0,0,0', '_.ZOOM', '_E', '_.LIST', '_ALL', '', '_.MASSPROP', '_ALL', '', '_N'
A '-WBLOCK', $Destino, '*'

$texto = Invoke-ConsolaIxCad -Dwg $Origem -Linhas $L.ToArray() -Log "$Destino.log"
if (-not (Test-Path $Destino)) { throw "Nao foi gravado $Destino (ver $Destino.log)" }
$ents = @(ConvertFrom-ListaConsola $texto)
if ($ents.Count -ne 1 -or $ents[0].Tipo -ne '3DSOLID') {
    Write-Warning ("Esperava 1 solido e ficaram {0} entidades: a UNION falhou? Ver {1}.log" -f $ents.Count, $Destino)
}
foreach ($e in $ents) { Write-Host ("{0} camada {1}  min {2}  max {3}" -f $e.Tipo, $e.Camada, (Format-Ponto $e.Min), (Format-Ponto $e.Max)) }
Write-Host ("Gravado {0} ({1:N0} kB)" -f $Destino, ((Get-Item $Destino).Length / 1KB))
