<#
.SYNOPSIS
    Cria o DWT da moldura de obra A3 horizontal DV_A3_Obra (legenda neutra, sem nome da empresa).

.DESCRIPTION
    Parte da moldura de obra A3 do kit (DmLayout_DinA3_order.dwt), para herdar a pagina
    "PDF_LS_A3" (A3 horizontal, plotter PDF). Apaga a moldura e as 4 janelas do kit e desenha:

      - moldura 400 x 270 mm (a do kit tem o mesmo tamanho) e margem interior de 5 mm;
      - legenda 180 x 26 mm em baixo a direita, com os campos que o iMos preenche:
          Cliente (IMOSORDERCUSTOMER)   Obra / Encomenda (IMOSORDERID)   Data (IMOSORDERACTDATE)
          Desenho (IMOSVSLAYOUTNAME)    Escala (IMOSVSSCALE)   Folha (IMOSVSLAYOUTPAGE)
          Desenhador (IMOSORDEREMPLOYEE)
        Os campos nao tem valor por defeito: se o iMos nao os preencher, ficam em branco
        (nunca aparece o nome do campo, como acontecia na moldura STANDARD);
      - UMA janela (viewport) grande por cima da legenda, para a vista.

    A legenda e' um bloco (DV_A3_Legenda) com atributos, como a do kit. O layout passa a
    chamar-se DV_A3_Obra. Nada de "Lanca Encanto" nem "LE": a LE trabalha para outros clientes.

    O DWT fica num ficheiro; quem o grava na base (BINDATA) e' o configurar_dv.py --moldura.

.EXAMPLE
    .\criar_moldura_a3.ps1 -Saida C:\temp\dv_moldura
#>
param(
    [Parameter(Mandatory)][string]$Saida,
    [string]$Kit = 'I:\Library\Bord\DmLayout_DinA3_order.dwt'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_dv_comum.ps1')

New-Item -ItemType Directory -Force $Saida | Out-Null
$base = Join-Path $Saida 'kit_DinA3_order.base.dwg'
$dwg = Join-Path $Saida 'DV_A3_Obra.dwg'
if (Test-Path $dwg) { throw "Ja existe: $dwg (apagar a mao antes de repetir)" }
Copy-Item $Kit $base -Force

# legenda: x 215..395, y 5..31; linha do meio em y=18
$x0, $x1, $y0, $ym, $y1 = 215, 395, 5, 18, 31
$cima = @(@{x = 215; c = 'Cliente'; t = 'IMOSORDERCUSTOMER'; h = 3.0 },
          @{x = 295; c = 'Obra / Encomenda'; t = 'IMOSORDERID'; h = 2.6 },
          @{x = 355; c = 'Data'; t = 'IMOSORDERACTDATE'; h = 2.6 })
$baixo = @(@{x = 215; c = 'Desenho'; t = 'IMOSVSLAYOUTNAME'; h = 3.0 },
           @{x = 295; c = 'Escala'; t = 'IMOSVSSCALE'; h = 3.0 },
           @{x = 320; c = 'Folha'; t = 'IMOSVSLAYOUTPAGE'; h = 3.0 },
           @{x = 340; c = 'Desenhador'; t = 'IMOSORDEREMPLOYEE'; h = 2.6 })

Reset-AttDef
$L = @(Get-InicioScript) + @('ATTREQ', '0', 'ATTDIA', '0', '_.PSPACE', '_.ERASE', '_ALL', '')
# o estilo "IMOS" do kit tem altura fixa (o -ATTDEF deixa de perguntar a altura e o script
# desalinha); o "Arial" do kit tem altura livre. A consola nao tem -STYLE.
$L += @('TEXTSTYLE', 'Arial')
# moldura exterior fina e interior a 0,5 mm
$L += @('_.RECTANG', '_W', '0', '_NON', '0,0', '_NON', '400,270')
$L += @('_.RECTANG', '_W', '0.5', '_NON', '5,5', '_NON', '395,265')
$L += @('_.RECTANG', '_W', '0', '_NON', "$x0,$y0", '_NON', "$x1,$y1")
$L += Linha $x0 $ym $x1 $ym
foreach ($c in $cima) { if ($c.x -gt $x0) { $L += Linha $c.x $ym $c.x $y1 } }
foreach ($c in $baixo) { if ($c.x -gt $x0) { $L += Linha $c.x $y0 $c.x $ym } }
foreach ($par in @(@{l = $cima; yt = $y1; yb = $ym }, @{l = $baixo; yt = $ym; yb = $y0 })) {
    foreach ($c in $par.l) {
        $L += Texto $c.c 'TL' ($c.x + 1.2) ($par.yt - 1.2) 1.6
        $L += AttDef $c.t 'BL' ($c.x + 1.5) ($par.yb + 2.2) $c.h
    }
}
# tudo o que esta' dentro da legenda vira o bloco DV_A3_Legenda, ja inserido no lugar
# (a consola nao tem -INSERT: usa-se o modo "Convert to block" do -BLOCK)
$L += @('-BLOCK', 'DV_A3_Legenda', 'O', 'C', '_NON', '0,0', '_W', '_NON', "$($x0 - 1),$($y0 - 1)", '_NON', "$($x1 + 1),$($y1 + 1)", '')
# janela da vista, por cima da legenda
$L += @('_.MVIEW', '_NON', '7,35', '_NON', '393,263')
$L += @('LAYOUT', '_R', 'DinA3_order', 'DV_A3_Obra')
$L += @('_.SAVEAS', '2018', $dwg)

$log = Invoke-ConsolaIxCad -Dwg $base -Linhas $L -Log (Join-Path $Saida 'DV_A3_Obra.log') -TimeoutSec 120
if (-not (Test-Path $dwg)) { throw "Nao gravou $dwg (ver DV_A3_Obra.log)" }
"Criado: $dwg"
