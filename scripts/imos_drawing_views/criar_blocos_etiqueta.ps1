<#
.SYNOPSIS
    Cria os blocos de etiqueta DV_* das Drawing Views (nome e medidas do modulo, medidas das frentes).

.DESCRIPTION
    O iMos insere as etiquetas a escala 1 no espaco modelo (confirmado a 05-10 na
    ORC_260881_2604023). Por isso os blocos vao desenhados em MILIMETROS DO MODELO, a medida
    de uma folha a 1:20 (texto de 50 mm no modelo = 2,5 mm no papel; a 1:25 da 2 mm).

    NAO sao anotativos. Um bloco anotativo so cresce se a escala de anotacao do desenho
    estiver a 1:20, mas com 1:20 as cotas do iMos (estilos IMOS_VIEW_*, tambem anotativos)
    ficam 20 vezes maiores. Por isso parte-se do _Medidas_Artigo.DWG, que nao e' anotativo.

      DV_Etq_Modulo(_r)  moldura 600 x 200: nome do modulo + "L x A x P" (alcado)
      DV_Etq_Nome(_r)    moldura 400 x 90: so o nome do modulo (planta; as medidas vao na tabela)
      DV_Etq_Frente      "L x A" da porta / frente de gaveta, sem moldura

    O _r e' a mesma etiqueta rodada 180 graus. O iMos usa-a na planta quando o modulo esta
    virado ao contrario, para o texto nunca ficar de pernas para o ar.

    -Instalar copia para I:\Library\AttDWG. O I: nao tem Reciclagem: nunca grava por cima
    (se o nome ja existir, para e diz qual e').

.EXAMPLE
    .\criar_blocos_etiqueta.ps1 -Saida C:\temp\dv_att
    .\criar_blocos_etiqueta.ps1 -Saida C:\temp\dv_att -Instalar
#>
param(
    [Parameter(Mandatory)][string]$Saida,
    [switch]$Instalar,
    [string]$Biblioteca = 'I:\Library\AttDWG',
    # 'papel' (volta 2, por defeito): anotativos, mm de papel, texto colorido, sem moldura.
    # 'modelo' (volta 1.5): mm do modelo para 1:20, nao anotativos, com moldura.
    [ValidateSet('papel', 'modelo')][string]$Versao = 'papel'
)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '_dv_comum.ps1')

New-Item -ItemType Directory -Force $Saida | Out-Null

# cada bloco comeca numa consola nova, e o ultimo campo de cada lista deixa o modo
# "Constant" desligado, por isso a ordem abaixo conta
Reset-AttDef
if ($Versao -eq 'modelo') {
    $modelo = Join-Path $Biblioteca '_Medidas_Artigo.DWG'
    $estilo = 'IMOS'
    $blocos = [ordered]@{
        'DV_Etq_Modulo' = @(
            @('_.RECTANG', '_NON', '-300,-100', '_NON', '300,100')
            AttDef 'IMOSELEMENTARTICLE' 'MC' 0 38 50
            AttDef 'IMOSARTICLEWIDTH' 'MR' -95 -50 34
            Texto 'x' 'MC' -80 -50 34
            AttDef 'IMOSARTICLEHEIGHT' 'MC' 0 -50 34
            Texto 'x' 'MC' 80 -50 34
            AttDef 'IMOSARTICLEDEPTH' 'ML' 95 -50 34
        )
        'DV_Etq_Nome' = @(
            @('_.RECTANG', '_NON', '-200,-45', '_NON', '200,45')
            AttDef 'IMOSELEMENTARTICLE' 'MC' 0 0 50
        )
        'DV_Etq_Frente' = @(
            AttDef 'IMOSPARTWIDTH' 'MR' -18 0 34
            Texto 'x' 'MC' 0 0 34
            AttDef 'IMOSPARTHEIGHT' 'ML' 18 0 34
        )
    }
    $rodar = @('DV_Etq_Modulo', 'DV_Etq_Nome')
    $cores = @{}
} else {
    # Volta 2 (05-10, tarde): o Output batch acerta a escala de anotacao pela escala da
    # folha, por isso as etiquetas voltam a ser anotativas, em mm de PAPEL (parte do
    # Article_PosName, que e' anotativo). Sem moldura e com o texto na cor da posicao:
    # vermelho para os modulos acima de 1490 mm, azul para os outros (pedido do Paulo).
    # A frente usa os campos PXM da peca (COND.PART_SIZE_*) para ver se saem sem as duas
    # casas decimais do IMOSPARTWIDTH ("446.50").
    $modelo = Join-Path $Biblioteca 'Article_PosName.dwg'
    $estilo = 'STANDARD'
    $modulo = {
        AttDef 'IMOSELEMENTARTICLE' 'MC' 0 1.5 2.5
        AttDef 'IMOSARTICLEWIDTH' 'MR' -4.7 -1.7 1.8
        Texto 'x' 'MC' -3.9 -1.7 1.8
        AttDef 'IMOSARTICLEHEIGHT' 'MC' 0 -1.7 1.8
        Texto 'x' 'MC' 3.9 -1.7 1.8
        AttDef 'IMOSARTICLEDEPTH' 'ML' 4.7 -1.7 1.8
    }
    $blocos = [ordered]@{
        'DV_Lbl_Modulo_Azul' = @(& $modulo)
        'DV_Lbl_Modulo_Verm' = @(& $modulo)
        'DV_Lbl_Nome_Azul'   = @(AttDef 'IMOSELEMENTARTICLE' 'MC' 0 0 2.5)
        'DV_Lbl_Nome_Verm'   = @(AttDef 'IMOSELEMENTARTICLE' 'MC' 0 0 2.5)
        'DV_Lbl_Frente'      = @(
            AttDef 'COND.PART_SIZE_X' 'MR' -0.9 0 1.8
            Texto 'x' 'MC' 0 0 1.8
            AttDef 'COND.PART_SIZE_Y' 'ML' 0.9 0 1.8
        )
    }
    $rodar = @('DV_Lbl_Modulo_Azul', 'DV_Lbl_Modulo_Verm', 'DV_Lbl_Nome_Azul', 'DV_Lbl_Nome_Verm', 'DV_Lbl_Frente')
    $cores = @{ 'Azul' = '5'; 'Verm' = '1' }
}

$feitos = @()
foreach ($nome in $blocos.Keys) {
    foreach ($r in @($false, $true)) {
        if ($r -and $rodar -notcontains $nome) { continue }
        $final = if ($r) { "${nome}_r" } else { $nome }
        $base = Join-Path $Saida "$final.base.dwg"
        $dwg = Join-Path $Saida "$final.dwg"
        if (Test-Path $dwg) { throw "Ja existe: $dwg (apagar a mao antes de repetir)" }
        Copy-Item $modelo $base -Force
        # estilo de texto com altura livre (o STANDARD do _Medidas_Artigo tem altura fixa 150:
        # o -ATTDEF deixaria de perguntar a altura)
        $L = @(Get-InicioScript) + @('ATTREQ', '0', 'ATTDIA', '0', 'TEXTSTYLE', $estilo, '_.ERASE', '_ALL', '')
        foreach ($c in $cores.Keys) { if ($nome -like "*_$c") { $L += @('CECOLOR', $cores[$c]) } }
        $L += $blocos[$nome] | ForEach-Object { $_ }
        if ($r) { $L += @('_.ROTATE', '_ALL', '', '_NON', '0,0', '180') }
        $L += @('_.ZOOM', '_E', '_.SAVEAS', '2018', $dwg)
        $log = Invoke-ConsolaIxCad -Dwg $base -Linhas $L -Log (Join-Path $Saida "$final.log") -TimeoutSec 120
        if (-not (Test-Path $dwg)) { throw "Nao gravou $dwg (ver $final.log)" }
        $feitos += $dwg
    }
}
"Criados:"; $feitos

if ($Instalar) {
    foreach ($f in $feitos) {
        $destino = Join-Path $Biblioteca (Split-Path $f -Leaf)
        if (Test-Path $destino) { throw "Ja existe na biblioteca (nao gravo por cima): $destino" }
    }
    foreach ($f in $feitos) { Copy-Item $f $Biblioteca; "Instalado: $(Join-Path $Biblioteca (Split-Path $f -Leaf))" }
}
