<#
.SYNOPSIS
    Funcoes comuns para usar o kernel CAD do iX CAD (imos) sem abrir o programa.

.DESCRIPTION
    Carregar no inicio de cada script destas ferramentas:

        . "$PSScriptRoot\_consola.ps1"

    O iX CAD 2025 traz uma consola AutoCAD OEM (accoreconsole.exe) que corre
    scripts .scr sobre um DWG, sem janela. E' por ela que se converte, corta e
    monta as ferragens. Limites desta versao OEM (ver README.md):
      - nao ha LISP, PURGE, MESHSMOOTH, STLOUT, SURFSCULPT, 3DOSMODE;
      - NETLOAD de DLL propria da "Security error" (bloqueio da imos: nao contornar);
      - OSNAPCOORD vem a 2 -> nos scripts o snap come as coordenadas escritas.
        Get-InicioScript poe OSNAPCOORD 1 e os pontos criticos levam "_NON".
      - um comando desconhecido ou uma selecao vazia ("None found") desalinha o
        resto do script: a consola fica a responder ao que nao devia.
#>

$IxFerramentas = $PSScriptRoot

function Get-KernelIxCad {
    # Pasta do kernel (accoreconsole.exe + AcTranslators.exe). IXCAD_KERNEL manda, se existir.
    if ($env:IXCAD_KERNEL) { return $env:IXCAD_KERNEL }
    $c = Get-ChildItem 'C:\Program Files\imos AG' -Directory -Filter 'iX CAD*' -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        ForEach-Object { Join-Path $_.FullName 'CAD-Kernel' } |
        Where-Object { Test-Path (Join-Path $_ 'accoreconsole.exe') } |
        Select-Object -First 1
    if (-not $c) { throw 'Nao encontrei o kernel do iX CAD (accoreconsole.exe). Definir a variavel IXCAD_KERNEL.' }
    $c
}

function Format-Ponto {
    # (1.5, 2, -3) -> "1.5,2,-3" sempre com ponto decimal
    param([double[]]$Valores)
    $ci = [Globalization.CultureInfo]::InvariantCulture
    ($Valores | ForEach-Object { $_.ToString('0.####', $ci) }) -join ','
}

function Get-InicioScript {
    # Primeiras linhas de qualquer script: sem dialogos e sem snaps a mexer nos pontos.
    @('FILEDIA', '0', 'CMDDIA', '0', 'OSMODE', '0', 'OSNAPCOORD', '1')
}

function Invoke-ConsolaIxCad {
    <#
    Corre as linhas dadas como script sobre o DWG. Grava o .scr e o registo
    (texto) ao lado do $Log e devolve o texto do registo. Se a consola ficar
    parada numa pergunta, mata-a ao fim de $TimeoutSec e da erro.
    O DWG de entrada nunca e' gravado por cima (os scripts usam SAVEAS/-WBLOCK
    para ficheiros novos).
    #>
    param(
        [Parameter(Mandatory)][string]$Dwg,
        # as linhas vazias sao o "Enter" da consola
        [Parameter(Mandatory)][AllowEmptyString()][string[]]$Linhas,
        [Parameter(Mandatory)][string]$Log,
        [int]$TimeoutSec = 300
    )
    $exe = Join-Path (Get-KernelIxCad) 'accoreconsole.exe'
    $scr = [IO.Path]::ChangeExtension($Log, '.scr')
    ($Linhas -join "`r`n") + "`r`n" | Set-Content -Encoding ascii -NoNewline $scr
    $bruto = "$Log.utf16"
    $argumentos = @('/i', "`"$Dwg`"", '/s', "`"$scr`"", '/l', 'en-US')
    $p = Start-Process -FilePath $exe -ArgumentList $argumentos -NoNewWindow -PassThru `
        -RedirectStandardOutput $bruto -WorkingDirectory (Split-Path $Dwg)
    $acabou = $p.WaitForExit($TimeoutSec * 1000)
    if (-not $acabou) {
        $p.Kill()
        $p.WaitForExit(15000) | Out-Null
        Start-Sleep -Milliseconds 500
    }
    $texto = [Text.Encoding]::Unicode.GetString([IO.File]::ReadAllBytes($bruto))
    [IO.File]::WriteAllText($Log, $texto, (New-Object Text.UTF8Encoding($false)))
    if (-not $acabou) { throw "A consola ficou parada (provavelmente numa pergunta). Ver o fim de $Log" }
    if ($texto -match 'Unknown command "([^"]+)"') { Write-Warning "Comando desconhecido na consola: $($Matches[1]) (ver $Log)" }
    $texto
}

function ConvertFrom-ListaConsola {
    <#
    Le a saida do comando LIST e devolve um objeto por entidade:
    Tipo (3DSOLID, SURFACE, BLOCK REFERENCE, ...), Camada, Bloco, Min, Max (x,y,z).
    #>
    param([Parameter(Mandatory)][string]$Texto)
    $ci = [Globalization.CultureInfo]::InvariantCulture
    $fora = New-Object System.Collections.Generic.List[object]
    $atual = $null
    foreach ($linha in ($Texto -split "`r?`n")) {
        if ($linha -match '^\s{6,}(?<tipo>[A-Z0-9][A-Z0-9 ]*?)\s+Layer: "(?<camada>[^"]*)"') {
            $atual = [pscustomobject]@{ Tipo = $Matches.tipo.Trim(); Camada = $Matches.camada; Bloco = ''; Min = $null; Max = $null }
            $fora.Add($atual)
        } elseif ($atual -and $linha -match 'Block Name: "(?<b>[^"]*)"') {
            $atual.Bloco = $Matches.b
        } elseif ($atual -and $linha -match '(?<qual>Lower|Upper) Bound X = (?<x>\S+)\s*, Y = (?<y>\S+)\s*, Z = (?<z>\S+)') {
            $v = @([double]::Parse($Matches.x, $ci), [double]::Parse($Matches.y, $ci), [double]::Parse($Matches.z, $ci))
            if ($Matches.qual -eq 'Lower') { $atual.Min = $v } else { $atual.Max = $v }
        }
    }
    $fora
}

function Get-PythonMartelo {
    # Python do .venv do Martelo (tem numpy, scipy, Pillow, matplotlib e PySide6).
    $raiz = (Resolve-Path (Join-Path $IxFerramentas '..\..')).Path
    $candidatos = @(Join-Path $raiz '.venv\Scripts\python.exe')
    $i = $raiz.IndexOf('\.claude\worktrees\')
    if ($i -gt 0) { $candidatos += (Join-Path $raiz.Substring(0, $i) '.venv\Scripts\python.exe') }
    foreach ($c in $candidatos) { if (Test-Path $c) { return $c } }
    'python'
}

function Assert-NaoExiste {
    # Estas ferramentas nunca gravam por cima de nada.
    param([string[]]$Caminhos)
    foreach ($c in $Caminhos) {
        if (Test-Path $c) { throw "Ja existe: $c -- escolher outro nome ou outra pasta (nada e' apagado nem substituido)." }
    }
}
