<#
    Funcoes comuns aos scripts das Drawing Views (blocos de etiqueta e moldura).
    Carregar com:  . "$PSScriptRoot\_dv_comum.ps1"

    A consola do iX CAD nao tem TEXT nem MTEXT: o texto fixo e' feito com atributos
    constantes (-ATTDEF modo C). O modo "Constant" fica memorizado de um -ATTDEF para o
    seguinte, por isso cada funcao liga-o ou desliga-o conforme o estado anterior.
    Comecar cada script novo da consola com Reset-AttDef.
#>
. (Join-Path $PSScriptRoot '..\imos_ferragens\_consola.ps1')

$script:constante = $false
$script:nTexto = 0

function Reset-AttDef { $script:constante = $false }

function AttDef([string]$Tag, [string]$Just, [double]$X, [double]$Y, [double]$H) {
    # campo do iMos: sem pergunta nem valor por defeito (vazio = nunca aparece o nome do campo)
    $modo = if ($script:constante) { @('C', '') } else { @('') }
    $script:constante = $false
    @('-ATTDEF') + $modo + @($Tag, '', '', 'J', $Just, (Format-Ponto $X, $Y), (Format-Ponto $H), '0')
}

function Texto([string]$T, [string]$Just, [double]$X, [double]$Y, [double]$H) {
    # texto fixo (atributo constante). Sem acentos: o script vai em ASCII.
    $script:nTexto++
    $modo = if ($script:constante) { @('') } else { @('C', '') }
    $script:constante = $true
    @('-ATTDEF') + $modo + @("DV_TXT$($script:nTexto)", $T, 'J', $Just, (Format-Ponto $X, $Y), (Format-Ponto $H), '0')
}

function Linha([double]$X1, [double]$Y1, [double]$X2, [double]$Y2) {
    @('_.LINE', '_NON', (Format-Ponto $X1, $Y1), '_NON', (Format-Ponto $X2, $Y2), '')
}
