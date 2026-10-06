<#
.SYNOPSIS
    Cria o DWT da moldura de obra A3 horizontal DV_A3_Obra (legenda neutra, sem nome da empresa).

.DESCRIPTION
    Parte da moldura de obra A3 do kit (DmLayout_DinA3_order.dwt), para herdar a pagina
    "PDF_LS_A3" (A3 horizontal, plotter PDF). Apaga tudo o que o kit tem no layout e desenha
    (versao 8, pedido do Paulo a 05-10: "so o retangulo exterior e o da legenda"):

      - UM retangulo exterior de 406 x 272 mm (a area imprimivel do A3 "expand" e' 408 x 275);
      - a legenda, 180 x 22 mm, encostada ao canto inferior direito da moldura, com os campos
        que o iMos preenche:
          Cliente (IMOSORDERCUSTOMER)   Obra / Encomenda (IMOSORDERID)   Data (IMOSORDERACTDATE)
          Desenho (IMOSVSLAYOUTNAME)    Escala (IMOSVSSCALE)   Folha (IMOSVSLAYOUTPAGE)
          Desenhador (IMOSORDEREMPLOYEE)
        Os campos nao tem valor por defeito: se o iMos nao os preencher, ficam em branco;
      - UMA janela (viewport) com toda a largura, por cima da legenda, num layer que nao
        imprime (DV_JANELA): no PDF so ficam a moldura e a legenda.

    Tudo esta CENTRADO NA ORIGEM (0,0). O iMos cria cada layout novo com a vista do papel
    centrada em (0,0) (lido no DWG da obra a 05-10): com a moldura de 0,0 a 400,270 o layout
    abria descentrado e o Paulo tinha de o centrar a mao.

    A legenda e' um bloco (DV_A3_Legenda) com atributos, como a do kit. O layout passa a
    chamar-se DV_A3_Obra. Nada de "Lanca Encanto" nem "LE": a LE trabalha para outros clientes.

    O DWT fica num ficheiro; quem o grava na base (BINDATA) e' o configurar_dv.py --moldura.

    Com -Legenda Roupeiro (pedido do Paulo, 06-10) faz a moldura DV_A3_Roupeiro, do Output
    batch DV_Roupeiros: legenda de 2 linhas, sem Descricao nem Cliente, com o Artigo
    (numero de posicao, IMOSARTICLEPOSITION) e a Ref. cliente mais larga.

.EXAMPLE
    .\criar_moldura_a3.ps1 -Saida C:\temp\dv_moldura
    .\criar_moldura_a3.ps1 -Saida C:\temp\dv_roupeiro -Legenda Roupeiro
#>
param(
    [Parameter(Mandatory)][string]$Saida,
    # Obra = legenda de 3 linhas (DV_A3_Obra); Roupeiro = 2 linhas com o artigo (DV_A3_Roupeiro)
    [ValidateSet('Obra', 'Roupeiro')][string]$Legenda = 'Obra',
    # DWG/DWT de partida. Por defeito a moldura de obra A3 do kit; para refazer o layout "1"
    # do modelo de obra: -Kit <copia do config\IMOS.dwt> -LayoutOrigem 1 -LayoutNome 1
    # -PaginaPdf Layouts_PDFs (o assistente "Layouts" usa esse layout, 05-10).
    [string]$Kit = 'I:\Library\Bord\DmLayout_DinA3_order.dwt',
    [string]$LayoutOrigem = 'DinA3_order',
    [string]$LayoutNome = 'DV_A3_Obra',
    [string]$PaginaPdf = 'PDF_LS_A3',
    # DV_PlotStyle.ctb (criar_ctb_dv.py): o iX_PlotStyle com a cor 254 das linhas escondidas
    # escurecida. Tem de estar em I:\Plotters\Plot Styles.
    [string]$EstiloImpressao = 'DV_PlotStyle.ctb',
    # O iMos guarda o bloco na obra como '<nome>.<moldura>' e, se ja existir, usa a definicao
    # antiga (05-10: a legenda da v7 apareceu fora da folha v8). Cada desenho novo da legenda
    # leva um nome novo.
    [string]$NomeLegenda = 'DV_A3_Legenda_v10',
    # Sem DXF: a pagina acerta-se com -PLOT (detalhado, "Save changes to page setup") em vez
    # de editar o DXF. Obrigatorio para o IMOS.dwt: a volta pelo DXF perde dados do iMos
    # (8,1 MB -> 4,6 MB, 05-10). O deslocamento depende da pagina; para o layout "1" (A3
    # "full bleed") foi medido num PDF de teste: 203.6,-1.1 centra a moldura na folha.
    [switch]$SemDxf,
    [string]$OffsetPlot = '203.6,-1.1',
    # Layout para o Document Manager (R6, 06-10: folha com a perspetiva): a janela leva um nome
    # (XDATA IMOS / DocMan / "UserName:<nome>", como os layouts da LE) e uma vista 3D. Sem
    # nome, o Document Manager nao a encontra.
    [string]$JanelaDocMan,
    # direcao da vista: frente-esquerda e de cima (num roupeiro em L, contra a parede do fundo
    # e a da direita, ve-se a frente das duas pernas)
    [string]$VistaDir = '-1,-1,0.7',
    # estilo visual da janela, pelo nome do VISUALSTYLE: Realistic, como o layout "1" do Paulo.
    # A consola nao tem -VPOINT: a direcao (16/26/36) e o estilo (348) mudam-se no DXF.
    [string]$EstiloVisual = 'Realistic'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_dv_comum.ps1')
if ($Legenda -eq 'Roupeiro') {
    if (-not $PSBoundParameters.ContainsKey('LayoutNome')) { $LayoutNome = 'DV_A3_Roupeiro' }
    if (-not $PSBoundParameters.ContainsKey('NomeLegenda')) { $NomeLegenda = 'DV_A3_Legenda_Roup_v3' }
}

New-Item -ItemType Directory -Force $Saida | Out-Null
$base = Join-Path $Saida 'base.dwg'
$dwg = Join-Path $Saida "$LayoutNome.dwg"
if (Test-Path $dwg) { throw "Ja existe: $dwg (apagar a mao antes de repetir)" }
Copy-Item $Kit $base -Force

# moldura: x -203..203, y -136..136
$mx, $my = 203, 136
# legenda v10: 220 x 33 no canto inferior direito, 3 linhas de 11 mm, com os campos que o
# Paulo usa (nomes da LE no imos.msg -> campo original do iMos):
#   "Enc PHC" = Commission (IMOSORDERCOMMISSION)  "Ref Cliente" = Item number (IMOSORDERITEM)
#   "Nome Enc IMOS IX" = Series (IMOSORDERSERIES)  "Data_entrega" = IMOSORDERDELIVERYDATE
#   "Data Inicio" (Start of production) nao existe como atributo de moldura no iX 2025.
#   O cliente esta' no CLIENT (IMOSORDERCLIENT); o IMOSORDERCUSTOMER vem vazio.
$x0, $x1, $y0 = ($mx - 220), $mx, (-$my)
$ym, $ym2, $y1 = ($y0 + 11), ($y0 + 22), ($y0 + 33)
if ($Legenda -eq 'Roupeiro') {
    # 2 linhas de 11 mm (06-10): em cima os dados da encomenda, em baixo os da folha. Sem
    # Descricao nem Cliente (pedido do Paulo); a Ref. cliente alarga.
    # Artigo (RP_A_01): NAO HA campo de moldura que o batch preencha. Testados nas folhas do
    # batch (sao de obra, nao de artigo) e todos VAZIOS: IMOSARTICLEPOSITION (R1),
    # IMOSARTICLEPOSITIONHIERARCHY, IMOSARTICLENAME, IMOSELEMENTARTICLE,
    # IMOSELEMENTGROUPPOSITION, IMOSVSDESCRIPT e IMOSPLANPOSNAME (R2). O artigo vai nas
    # etiquetas do desenho; a celula saiu na v3.
    $y1 = $ym2
    $linhasLegenda = @(
        @{ yb = $ym; yt = $y1; celulas = @(
            @{x = 0; c = 'Nome enc. iMOS'; t = 'IMOSORDERSERIES'; h = 3.0 },
            @{x = 70; c = 'Enc. PHC'; t = 'IMOSORDERCOMMISSION'; h = 3.0 },
            @{x = 95; c = 'Ref. cliente'; t = 'IMOSORDERITEM'; h = 3.0 },
            @{x = 145; c = 'Obra'; t = 'IMOSORDERID'; h = 2.6 },
            @{x = 192; c = 'Entrega'; t = 'IMOSORDERDELIVERYDATE'; h = 2.4 }) },
        @{ yb = $y0; yt = $ym; celulas = @(
            @{x = 0; c = 'Desenho'; t = 'IMOSVSLAYOUTNAME'; h = 3.0 },
            @{x = 80; c = 'Escala'; t = 'IMOSVSSCALE'; h = 3.0 },
            @{x = 110; c = 'Folha'; t = 'IMOSVSLAYOUTPAGE'; h = 3.0 },
            @{x = 130; c = 'Desenhador'; t = 'IMOSORDEREMPLOYEE'; h = 2.6 },
            @{x = 180; c = 'Data'; t = 'IMOSORDERACTDATE'; h = 2.6 }) }
    )
}
else { $linhasLegenda = @(
    @{ yb = $ym2; yt = $y1; celulas = @(
        @{x = 0; c = 'Descri\U+00E7\U+00E3o'; t = 'IMOSORDERTEXTSHORT'; h = 2.4 },
        @{x = 140; c = 'Nome enc. iMOS'; t = 'IMOSORDERSERIES'; h = 2.6 }) },
    @{ yb = $ym; yt = $ym2; celulas = @(
        @{x = 0; c = 'Cliente'; t = 'IMOSORDERCLIENT'; h = 3.0 },
        @{x = 60; c = 'Enc. PHC'; t = 'IMOSORDERCOMMISSION'; h = 3.0 },
        @{x = 90; c = 'Ref. cliente'; t = 'IMOSORDERITEM'; h = 2.6 },
        @{x = 130; c = 'Obra'; t = 'IMOSORDERID'; h = 2.6 },
        @{x = 190; c = 'Entrega'; t = 'IMOSORDERDELIVERYDATE'; h = 2.6 }) },
    @{ yb = $y0; yt = $ym; celulas = @(
        @{x = 0; c = 'Desenho'; t = 'IMOSVSLAYOUTNAME'; h = 3.0 },
        @{x = 80; c = 'Escala'; t = 'IMOSVSSCALE'; h = 3.0 },
        @{x = 110; c = 'Folha'; t = 'IMOSVSLAYOUTPAGE'; h = 3.0 },
        @{x = 130; c = 'Desenhador'; t = 'IMOSORDEREMPLOYEE'; h = 2.6 },
        @{x = 180; c = 'Data'; t = 'IMOSORDERACTDATE'; h = 2.6 }) }
) }

Reset-AttDef
$L = @(Get-InicioScript) + @('ATTREQ', '0', 'ATTDIA', '0', 'LAYOUT', '_S', $LayoutOrigem, '_.PSPACE', '_.ERASE', '_ALL', '')
# o estilo "IMOS" do kit tem altura fixa (o -ATTDEF deixa de perguntar a altura e o script
# desalinha); o "Arial" do kit tem altura livre. A consola nao tem -STYLE.
$L += @('TEXTSTYLE', 'Arial')
if ($Legenda -eq 'Roupeiro') {
    # R4 (06-10): as etiquetas das vistas e os indicadores de alcado sao anotativos e so tem
    # a escala de anotacao da obra (1:16 na APAGAR_15): nas folhas a 1:20 e 1:25 nao
    # apareciam. Com ANNOALLVISIBLE = 1 (guardado por layout) aparecem a mesma.
    $L += @('ANNOALLVISIBLE', '1')
}
# moldura exterior a 0,5 mm e a legenda (linhas finas), encostada a moldura
$L += @('_.RECTANG', '_W', '0.5', '_NON', "-$mx,-$my", '_NON', "$mx,$my")
# topo da legenda: inclui a faixa de teste dos roupeiros, se houver
$yTopo = ($linhasLegenda | ForEach-Object { $_.yt } | Measure-Object -Maximum).Maximum
$L += @('_.RECTANG', '_W', '0', '_NON', "$x0,$y0", '_NON', "$x1,$yTopo")
foreach ($ln in $linhasLegenda) {
    if ($ln.yb -gt $y0) { $L += Linha $x0 $ln.yb $x1 $ln.yb }
}
foreach ($ln in $linhasLegenda) {
    foreach ($c in $ln.celulas) {
        $x = $x0 + $c.x
        if ($c.x -gt 0) { $L += Linha $x $ln.yb $x $ln.yt }
        $L += Texto $c.c 'TL' ($x + 1.2) ($ln.yt - 1.2) 1.6
        $L += AttDef $c.t 'BL' ($x + 1.5) ($ln.yb + 2.0) $c.h
    }
}
# tudo o que esta' dentro da legenda vira o bloco da legenda, ja inserido no lugar
# (a consola nao tem -INSERT: usa-se o modo "Convert to block" do -BLOCK). A selecao por
# janela so apanha o que esta' no ecra: com a moldura centrada na origem, ZOOM E antes. E so'
# apanha o que cabe todo na janela: os atributos medem-se pelo nome do campo, e o
# IMOSORDERDELIVERYDATE passava a direita da moldura (ficava fora do bloco): janela larga.
$L += @('_.ZOOM', '_E')
$L += @('-BLOCK', $NomeLegenda, 'O', 'C', '_NON', '0,0', '_W', '_NON', "$($x0 - 1),$($y0 - 1)", '_NON', "$($x1 + 80),$($yTopo + 1)", '')
# janela da vista: toda a largura, por cima da legenda, num layer que nao imprime
$L += @('-LAYER', '_M', 'DV_JANELA', '_P', '_N', 'DV_JANELA', '')
$L += @('_.MVIEW', '_NON', "$(-$mx + 2),$($yTopo + 2)", '_NON', "$($mx - 2),$($my - 2)")
$L += @('-LAYER', '_S', '0', '')
$L += @('_.ZOOM', '_E')
if ($LayoutNome -ne $LayoutOrigem) { $L += @('LAYOUT', '_R', $LayoutOrigem, $LayoutNome) }
$L += @('_.SAVEAS', '2018', $dwg)
$bruto = Join-Path $Saida 'passo1.dwg'
$L[-1] = $bruto
$log = Invoke-ConsolaIxCad -Dwg $base -Linhas $L -Log (Join-Path $Saida 'passo1.log') -TimeoutSec 120
if (-not (Test-Path $bruto)) { throw "Nao gravou $bruto (ver passo1.log)" }

if ($SemDxf) {
    $L2 = (Get-InicioScript) + @('LAYOUT', '_S', $LayoutNome, '-PLOT', '_Y', $LayoutNome, '', '', '', '', '',
        '_L', '1:1', $OffsetPlot, '_Y', $EstiloImpressao, '_Y', '', '', '', (Join-Path $Saida 'verificacao.pdf'), '_Y', '_Y',
        '_.SAVEAS', '2018', $dwg)
    Invoke-ConsolaIxCad -Dwg $bruto -Linhas $L2 -Log (Join-Path $Saida 'passo2.log') -TimeoutSec 240 | Out-Null
    if (-not (Test-Path $dwg)) { throw "Nao gravou $dwg (ver passo2.log)" }
    "Criado: $dwg (pagina por -PLOT, estilo $EstiloImpressao; ver verificacao.pdf)"
    return
}
# Estilo de impressao da pagina (I:\Plotters\Plot Styles). O iX_PlotStyle.ctb mantem o
# vermelho, azul e magenta das cotas e passa os cinzentos (8, 9, 250-253) a preto; o
# DV_PlotStyle.ctb faz o mesmo e escurece tambem a 254 das linhas escondidas. Sem eles, o PDF
# sai com as linhas escondidas e de fundo num cinzento quase invisivel (testes 05-10).
# A consola nao tem -PAGESETUP: muda-se o campo 7 do AcDbPlotSettings no DXF e volta a DWG.
$dxf = Join-Path $Saida 'passo2.dxf'
Invoke-ConsolaIxCad -Dwg $bruto -Linhas ((Get-InicioScript) + @('_.SAVEAS', '_DXF', '16', $dxf)) -Log (Join-Path $Saida 'passo2.log') -TimeoutSec 120 | Out-Null
#
# Na mesma passagem a pagina deixa de imprimir "Extents, ajustar a folha" e passa a
# "Layout, 1:1", com a origem deslocada para o centro do A3 (210 - margem esquerda,
# 148,5 - margem de baixo; margens do "ISO expand A3" = 5,79 / 10,79). A moldura, centrada
# na origem, sai assim centrada na folha e em tamanho real (testado com -PLOT na consola).
$ci = [Globalization.CultureInfo]::InvariantCulture
$pagina = @{ '7' = $EstiloImpressao; '74' = '5'; '75' = '16'; '142' = '1.0'; '143' = '1.0'; '147' = '1.0' }
$t = [IO.File]::ReadAllLines($dxf, [Text.Encoding]::Default)
$mudou = 0
for ($i = 0; $i -lt $t.Length - 3; $i++) {
    if ($t[$i].Trim() -eq '1' -and $t[$i + 1] -eq $PaginaPdf) {
        # o AcDbPlotSettings do layout e o da pagina com nome; acaba no "100" seguinte
        $margem = @{}
        for ($j = $i + 2; $j -lt [Math]::Min($i + 90, $t.Length - 1); $j += 2) {
            $c = $t[$j].Trim()
            if ($c -eq '100') { break }
            if ($c -in '40', '41') { $margem[$c] = [double]::Parse($t[$j + 1].Trim(), $ci) }
            if ($pagina.ContainsKey($c)) { $t[$j + 1] = $pagina[$c]; $mudou++ }
            if ($c -eq '70') { $t[$j + 1] = [string]([int]$t[$j + 1].Trim() -bor 16) }  # escala standard
            if ($c -eq '46') { $t[$j + 1] = (210 - $margem['40']).ToString($ci) }
            if ($c -eq '47') { $t[$j + 1] = (148.5 - $margem['41']).ToString($ci) }
        }
    }
}
if ($mudou -lt 1) { throw "Nao encontrei a pagina '$PaginaPdf' no DXF" }
if ($JanelaDocMan) {
    # nome da janela para o Document Manager: XDATA no fim da entidade VIEWPORT do layer
    # DV_JANELA (a aplicacao IMOS ja esta registada no kit)
    $lista = [Collections.Generic.List[string]]::new($t)
    # handle do estilo visual pedido (objeto VISUALSTYLE: 5 = handle, 2 = nome)
    $hEstilo = $null
    for ($i = 0; $i -lt $lista.Count - 1; $i += 2) {
        if ($lista[$i].Trim() -ne '0' -or $lista[$i + 1].Trim() -ne 'VISUALSTYLE') { continue }
        $h = $null
        for ($j = $i + 2; $j -lt $lista.Count -and $lista[$j].Trim() -ne '0'; $j += 2) {
            if ($lista[$j].Trim() -eq '5') { $h = $lista[$j + 1].Trim() }
            if ($lista[$j].Trim() -eq '2' -and $lista[$j + 1].Trim() -eq $EstiloVisual) { $hEstilo = $h }
        }
    }
    if (-not $hEstilo) { throw "Nao encontrei o estilo visual '$EstiloVisual' no DXF" }
    $dir = $VistaDir.Split(',')
    $feito = $false
    for ($i = 0; $i -lt $lista.Count - 1; $i += 2) {
        if ($lista[$i].Trim() -ne '0' -or $lista[$i + 1].Trim() -ne 'VIEWPORT') { continue }
        $fim = $i + 2
        while ($fim -lt $lista.Count -and $lista[$fim].Trim() -ne '0') { $fim += 2 }
        $layer = $null
        for ($j = $i + 2; $j -lt $fim; $j += 2) { if ($lista[$j].Trim() -eq '8') { $layer = $lista[$j + 1].Trim(); break } }
        if ($layer -ne 'DV_JANELA') { continue }
        for ($j = $i + 2; $j -lt $fim; $j += 2) {
            switch ($lista[$j].Trim()) {
                '16' { $lista[$j + 1] = $dir[0] }
                '26' { $lista[$j + 1] = $dir[1] }
                '36' { $lista[$j + 1] = $dir[2] }
                '348' { $lista[$j + 1] = $hEstilo }
            }
        }
        $xd =@('1001', 'IMOS', '1000', 'DocMan', '1002', '{', '1000', "UserName:$JanelaDocMan", '1002', '}')
        $lista.InsertRange($fim, [string[]]$xd)
        $feito = $true
        break
    }
    if (-not $feito) { throw "Nao encontrei a janela DV_JANELA no DXF" }
    $t = $lista.ToArray()
}
[IO.File]::WriteAllLines($dxf, $t, [Text.Encoding]::Default)
Invoke-ConsolaIxCad -Dwg $dxf -Linhas ((Get-InicioScript) + @('_.SAVEAS', '2018', $dwg)) -Log (Join-Path $Saida 'passo3.log') -TimeoutSec 120 | Out-Null
if (-not (Test-Path $dwg)) { throw "Nao gravou $dwg (ver passo3.log)" }
"Criado: $dwg (estilo de impressao $EstiloImpressao)"
