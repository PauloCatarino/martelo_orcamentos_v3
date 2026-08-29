<#
.SYNOPSIS
    Poe a copia de seguranca do Martelo V3 a correr todos os dias, sozinha.

.DESCRIPTION
    Cria uma tarefa no Agendador do Windows que corre o scripts\backup_martelo.py
    a` hora escolhida. Se o PC estiver desligado a essa hora, a tarefa corre
    assim que ele arrancar -- nunca se perde um dia por o PC ter estado em baixo.

    CORRER NO PC ONDE VIVE A BASE DE DADOS (o servidor), numa janela do
    PowerShell aberta COMO ADMINISTRADOR.

.EXAMPLE
    # O caso normal: copia local + copia no servidor, todos os dias a`s 03:00
    .\instalar_backup_agendado.ps1 -Base martelo_v3 -Copia "\\SERVER_LE\_Lanca_Encanto\LancaEncanto\Backups_Martelo"

.EXAMPLE
    # Ver o que ia fazer, sem criar nada
    .\instalar_backup_agendado.ps1 -Base martelo_v3 -Simular

.EXAMPLE
    # Tirar a tarefa
    .\instalar_backup_agendado.ps1 -Remover
#>

[CmdletBinding()]
param(
    # Base de dados a copiar.
    [string]$Base = "martelo_v3",

    # Pasta local das copias. Vazio = a pasta habitual do Martelo no PC.
    [string]$Pasta = "",

    # Segunda pasta, no servidor. E' ESTA que salva de um disco morto.
    [string]$Copia = "",

    # Hora a que corre, todos os dias.
    [string]$Hora = "03:00",

    # Nome da tarefa no Agendador.
    [string]$Nome = "Martelo V3 - copia de seguranca",

    # Mostrar o que ia fazer, sem criar nada.
    [switch]$Simular,

    # Apagar a tarefa em vez de a criar.
    [switch]$Remover,

    # Nao guardar password nenhuma: a tarefa corre so' quando a pessoa tiver
    # sessao iniciada no PC. Chega a`s pastas de rede na mesma.
    [switch]$SemPassword
)

$ErrorActionPreference = "Stop"

function Escrever($texto, $cor = "Gray") { Write-Host $texto -ForegroundColor $cor }

# --- Onde estao as coisas ---------------------------------------------------

$RaizProjeto = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $RaizProjeto ".venv\Scripts\python.exe"
$ScriptCopia = Join-Path $PSScriptRoot "backup_martelo.py"

Escrever ""
Escrever "Martelo V3 - copia de seguranca automatica" "White"
Escrever ""

# --- Remover ----------------------------------------------------------------

if ($Remover) {
    $existente = Get-ScheduledTask -TaskName $Nome -ErrorAction SilentlyContinue
    if ($null -eq $existente) {
        Escrever "Nao existe nenhuma tarefa chamada '$Nome'. Nada a fazer." "Yellow"
        exit 0
    }
    Escrever "Isto apaga SO' a tarefa agendada." "Yellow"
    Escrever "As copias ja' feitas ficam onde estao - nenhum ficheiro e' apagado." "Yellow"
    $resposta = Read-Host "Apagar a tarefa '$Nome'? (escreva SIM)"
    if ($resposta -ne "SIM") { Escrever "Cancelado." "Yellow"; exit 0 }
    Unregister-ScheduledTask -TaskName $Nome -Confirm:$false
    Escrever "Tarefa apagada." "Green"
    exit 0
}

# --- Verificacoes antes de criar seja o que for -----------------------------

if (-not (Test-Path $Python)) {
    Escrever "[ERRO] nao encontrei o Python do projeto:" "Red"
    Escrever "       $Python" "Red"
    Escrever "       Confirme que esta' a correr isto de dentro da pasta do Martelo V3." "Red"
    exit 1
}
if (-not (Test-Path $ScriptCopia)) {
    Escrever "[ERRO] nao encontrei o $ScriptCopia" "Red"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($Copia)) {
    Escrever "AVISO: nao indicou -Copia (a pasta no servidor)." "Yellow"
    Escrever "       A copia vai ficar so' no mesmo disco onde vive a base de dados." "Yellow"
    Escrever "       Isso protege de um apagao ou de um engano - nao protege do disco" "Yellow"
    Escrever "       avariar, que e' o caso que interessa." "Yellow"
    Escrever ""
    $continuar = Read-Host "Continuar assim mesmo? (S/N)"
    if ($continuar -notmatch '^[SsYy]') { Escrever "Cancelado." "Yellow"; exit 0 }
} else {
    Escrever "A confirmar que consigo escrever em $Copia ..."
    try {
        if (-not (Test-Path $Copia)) { New-Item -ItemType Directory -Path $Copia -Force | Out-Null }
        $teste = Join-Path $Copia ".martelo_teste_escrita"
        Set-Content -Path $teste -Value "ok" -Encoding utf8
        Remove-Item $teste -Force
        Escrever "   OK" "Green"
    } catch {
        Escrever "[ERRO] nao consigo escrever em $Copia" "Red"
        Escrever "       $($_.Exception.Message)" "Red"
        Escrever "       Confirme o caminho e as permissoes na pasta do servidor." "Red"
        exit 1
    }
}

# --- Montar o comando -------------------------------------------------------

$argumentos = @("`"$ScriptCopia`"", "--base", $Base)
if (-not [string]::IsNullOrWhiteSpace($Pasta)) { $argumentos += @("--pasta", "`"$Pasta`"") }
if (-not [string]::IsNullOrWhiteSpace($Copia)) { $argumentos += @("--copia", "`"$Copia`"") }
$linhaArgumentos = $argumentos -join " "

Escrever ""
Escrever "Vai ficar assim:" "White"
Escrever "   tarefa   : $Nome"
Escrever "   quando   : todos os dias a`s $Hora (e ao arrancar, se falhar a hora)"
Escrever "   base     : $Base"
Escrever "   comando  : $Python $linhaArgumentos"
Escrever ""

if ($Simular) { Escrever "(-Simular: nao criei nada.)" "Yellow"; exit 0 }

# --- Como e' que a tarefa entra ---------------------------------------------
# Para escrever numa pasta de rede, a tarefa precisa das credenciais de uma
# conta com acesso a essa pasta: uma tarefa "sem password guardada" (S4U) nao
# leva credenciais para a rede e as copias no servidor falhavam todas.
# Sem pasta de rede, basta correr quando a pessoa esta' com sessao iniciada.

$acao = New-ScheduledTaskAction -Execute $Python -Argument $linhaArgumentos -WorkingDirectory $RaizProjeto
$gatilhos = @(
    (New-ScheduledTaskTrigger -Daily -At $Hora)
)
$definicoes = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -DontStopOnIdleEnd `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

function Registar-ComSessaoIniciada {
    # A tarefa corre com a sessao de quem esta' no PC. Nao guarda password
    # nenhuma, e chega a`s pastas de rede na mesma -- mas so' corre enquanto
    # essa pessoa estiver com sessao iniciada. Com o -StartWhenAvailable, se a
    # hora passar sem sessao, a copia faz-se assim que ela entrar.
    $entrada = New-ScheduledTaskPrincipal `
        -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited
    Register-ScheduledTask -TaskName $Nome -Action $acao -Trigger $gatilhos `
        -Settings $definicoes -Principal $entrada -Force | Out-Null
}

$comPassword = (-not [string]::IsNullOrWhiteSpace($Copia)) -and (-not $SemPassword)

if ($comPassword) {
    Escrever "A tarefa vai escrever numa pasta de rede." "White"
    Escrever ""
    Escrever "Para correr MESMO QUANDO ninguem tem sessao iniciada no PC, o Windows" "White"
    Escrever "precisa de guardar a conta e a password de quem a corre. Quem as guarda" "White"
    Escrever "e' o Windows, nao o Martelo, e nao ficam em ficheiro nenhum do projeto." "White"
    Escrever ""
    Escrever "Se preferir nao dar a password, feche a janela que vai aparecer: a tarefa" "Yellow"
    Escrever "fica a correr so' quando o Paulo tiver sessao iniciada (que e' quase" "Yellow"
    Escrever "sempre, ja' que este PC e' o servidor da base de dados)." "Yellow"
    Escrever ""

    $credenciais = Get-Credential `
        -Message "Conta do Windows que corre a copia" `
        -UserName "$env:USERDOMAIN\$env:USERNAME"

    if ($null -eq $credenciais -or [string]::IsNullOrWhiteSpace($credenciais.UserName)) {
        Escrever "Nao deu credenciais. A criar a tarefa em modo 'com sessao iniciada'." "Yellow"
        Registar-ComSessaoIniciada
        $comPassword = $false
    } else {
        # O Agendador exige a conta qualificada (PC\utilizador). Se a pessoa
        # escrever so' o nome, o Windows recusa com "O parametro esta'
        # incorreto" -- uma mensagem que nao ajuda ninguem.
        $utilizador = $credenciais.UserName
        if ($utilizador -notmatch '[\\@]') { $utilizador = "$env:COMPUTERNAME\$utilizador" }
        $utilizador = $utilizador -replace '^\\', "$env:COMPUTERNAME\"

        try {
            Register-ScheduledTask -TaskName $Nome -Action $acao -Trigger $gatilhos `
                -Settings $definicoes `
                -User $utilizador `
                -Password $credenciais.GetNetworkCredential().Password `
                -RunLevel Limited -Force -ErrorAction Stop | Out-Null
            Escrever "Conta usada: $utilizador" "Gray"
        } catch {
            Escrever "O Windows recusou essa conta ou password:" "Red"
            Escrever "   $($_.Exception.Message)" "Red"
            Escrever ""
            Escrever "A criar a tarefa em modo 'com sessao iniciada', que nao precisa de" "Yellow"
            Escrever "password. Corre sempre que o Paulo tiver sessao aberta." "Yellow"
            Registar-ComSessaoIniciada
            $comPassword = $false
        }
    }
} else {
    Registar-ComSessaoIniciada
}

Escrever "Tarefa criada." "Green"
Escrever ""

# --- Correr uma vez agora, para nao ficar a fe' ------------------------------

Escrever "A correr uma copia agora, para confirmar que funciona..." "White"
Start-ScheduledTask -TaskName $Nome

$fim = (Get-Date).AddMinutes(5)
do {
    Start-Sleep -Seconds 3
    $estado = (Get-ScheduledTask -TaskName $Nome).State
} while ($estado -eq "Running" -and (Get-Date) -lt $fim)

$resultado = (Get-ScheduledTaskInfo -TaskName $Nome).LastTaskResult
if ($resultado -eq 0) {
    Escrever "   A primeira copia correu bem." "Green"
} else {
    Escrever "   A primeira copia devolveu o codigo $resultado." "Red"
    Escrever "   Veja o ficheiro backup.log na pasta das copias para saber porque." "Red"
}

Escrever ""
Escrever "A partir de agora:" "White"
if ($comPassword) {
    Escrever "  - a copia corre todos os dias a`s $Hora, mesmo sem ninguem no PC"
} else {
    Escrever "  - a copia corre todos os dias a`s $Hora, com sessao iniciada"
    Escrever "    (se a essa hora nao houver sessao, faz-se assim que entrar)"
}
Escrever "  - o que aconteceu fica em  backup.log  na pasta das copias"
Escrever "  - a ultima linha de estado fica em  ultima_copia.txt"
Escrever ""
Escrever "Uma vez por mes, vale a pena provar que uma copia restaura mesmo:" "White"
Escrever "  $Python `"$ScriptCopia`" --base $Base --testar-restauro"
Escrever ""
