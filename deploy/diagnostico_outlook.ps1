# Diagnostico do envio de emails do Martelo V3.
#
# PARA QUE SERVE
# --------------
# Quando o Martelo diz "Nao foi possivel ligar ao Outlook", a causa e' quase
# sempre uma de tres, e sao diferentes de resolver:
#   1. o Martelo esta' marcado no Windows para abrir SEMPRE como administrador
#      (o visto fica colado ao ficheiro: abrir pelo atalho NAO resolve);
#   2. a janela do Martelo foi aberta como administrador so' desta vez
#      (tipicamente o "Abrir" no fim do instalador);
#   3. o computador nao tem o Outlook classico do Office -- o "novo Outlook"
#      nao deixa outros programas prepararem emails.
#
# Este script diz qual delas e', sem instalar nada. Nao altera nada no
# computador: so' le' e escreve o resultado no ecra.
#
# COMO SE USA (no PC de quem tem o problema)
# ------------------------------------------
#   Botao direito neste ficheiro -> "Executar com o PowerShell"
# ou, numa janela do PowerShell:
#   powershell -ExecutionPolicy Bypass -File diagnostico_outlook.ps1

$ErrorActionPreference = "Continue"

function Escrever-Titulo($texto) {
    Write-Host ""
    Write-Host "== $texto ==" -ForegroundColor Cyan
}

Write-Host "Diagnostico do envio de emails do Martelo V3"
Write-Host "PC: $env:COMPUTERNAME   Utilizador: $env:USERNAME"
Write-Host ("Data: " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss"))

# ---------------------------------------------------------------------------
# Este script NAO PODE correr como administrador.
# O problema que estamos a investigar e' precisamente um programa elevado nao
# conseguir falar com o Outlook. Se esta janela estiver elevada, a "prova dos
# noves" la' em baixo falha SEMPRE -- e falha pela janela, nao pelo Martelo.
# Daria uma resposta errada, que e' pior do que nao dar resposta nenhuma.
# ---------------------------------------------------------------------------
$identidadeInicial = [Security.Principal.WindowsIdentity]::GetCurrent()
$principalInicial = New-Object Security.Principal.WindowsPrincipal($identidadeInicial)
$janelaElevada = $principalInicial.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($janelaElevada) {
    Write-Host ""
    Write-Host "  !!! ESTA JANELA DO POWERSHELL ESTA' A CORRER COMO ADMINISTRADOR !!!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Assim o teste nao serve: e' a propria janela que nao consegue" -ForegroundColor Yellow
    Write-Host "  falar com o Outlook, e nao ficamos a saber nada sobre o Martelo." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  FECHE esta janela e abra o PowerShell NORMAL:" -ForegroundColor Yellow
    Write-Host "    menu Iniciar -> escrever 'PowerShell' -> Enter" -ForegroundColor Yellow
    Write-Host "    (SEM 'Executar como administrador')" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Ou, mais simples: botao direito neste ficheiro ->" -ForegroundColor Yellow
    Write-Host "  'Executar com o PowerShell'." -ForegroundColor Yellow
    Write-Host ""
}

# ---------------------------------------------------------------- o executavel
Escrever-Titulo "Onde esta' o Martelo"

$candidatos = @(
    "$env:ProgramFiles\Martelo Orcamentos V3\Martelo_Orcamentos_V3.exe",
    "${env:ProgramFiles(x86)}\Martelo Orcamentos V3\Martelo_Orcamentos_V3.exe",
    "$env:LOCALAPPDATA\Programs\Martelo Orcamentos V3\Martelo_Orcamentos_V3.exe"
)
$exe = $null
foreach ($c in $candidatos) {
    if (Test-Path $c) { $exe = $c; break }
}
if (-not $exe) {
    $encontrado = Get-ChildItem -Path "$env:ProgramFiles", "$env:LOCALAPPDATA\Programs" `
        -Filter "Martelo_Orcamentos_V3.exe" -Recurse -ErrorAction SilentlyContinue |
        Select-Object -First 1
    if ($encontrado) { $exe = $encontrado.FullName }
}

if ($exe) {
    Write-Host "  $exe"
} else {
    Write-Host "  Nao encontrei o executavel instalado." -ForegroundColor Yellow
}

# ------------------------------------------------ CAUSA 1: marcado como admin
Escrever-Titulo "CAUSA 1 - marcado para abrir sempre como administrador"

$marcado = $false
$chave = "Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers"
foreach ($raiz in @("HKCU:", "HKLM:")) {
    $caminho = "$raiz\$chave"
    if (-not (Test-Path $caminho)) { continue }
    $props = Get-ItemProperty -Path $caminho -ErrorAction SilentlyContinue
    foreach ($p in $props.PSObject.Properties) {
        if ($p.Name -like "*Martelo*" -and $p.Value -match "RUNASADMIN") {
            Write-Host "  ENCONTRADO em ${raiz}:" -ForegroundColor Red
            Write-Host "    $($p.Name)"
            Write-Host "    $($p.Value)"
            $marcado = $true
        }
    }
}
if ($marcado) {
    Write-Host ""
    Write-Host "  >>> E' ESTA A CAUSA. Como resolver (uma vez so'):" -ForegroundColor Red
    Write-Host "      1. Ir ao ficheiro:  $exe"
    Write-Host "      2. Botao direito -> Propriedades -> separador Compatibilidade"
    Write-Host "      3. DESMARCAR 'Executar este programa como administrador' -> OK"
    Write-Host "      4. Fechar o Martelo e voltar a abrir"
    Write-Host "      (verificar tambem em 'Alterar definicoes para todos os utilizadores')"
} else {
    Write-Host "  Nao esta' marcado. Bom." -ForegroundColor Green
}

# ------------------------------------------- CAUSA 2: conta / UAC / elevacao
Escrever-Titulo "CAUSA 2 - a conta e o UAC"

Write-Host "  Esta janela do PowerShell esta' elevada: $janelaElevada"

$uac = Get-ItemProperty "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System" `
    -ErrorAction SilentlyContinue
if ($uac) {
    Write-Host "  EnableLUA (UAC ligado)      : $($uac.EnableLUA)"
    Write-Host "  ConsentPromptBehaviorAdmin  : $($uac.ConsentPromptBehaviorAdmin)"
    if ($uac.EnableLUA -eq 0) {
        Write-Host ""
        Write-Host "  >>> O UAC esta' DESLIGADO neste PC." -ForegroundColor Red
        Write-Host "      Com o UAC desligado, TUDO corre elevado -- incluindo o Outlook."
        Write-Host "      Nesse caso a culpa nao e' da elevacao: passe a` CAUSA 3."
    }
}

# ---------------------------------------------------- CAUSA 3: qual o Outlook
Escrever-Titulo "CAUSA 3 - que Outlook esta' instalado"

$classico = Test-Path "HKLM:\SOFTWARE\Classes\Outlook.Application\CLSID"
if (-not $classico) {
    $classico = Test-Path "Registry::HKEY_CLASSES_ROOT\Outlook.Application\CLSID"
}
if ($classico) {
    Write-Host "  Outlook classico (Office): SIM, com automacao registada." -ForegroundColor Green
} else {
    Write-Host "  Outlook classico (Office): NAO ENCONTRADO." -ForegroundColor Red
    Write-Host ""
    Write-Host "  >>> E' ESTA A CAUSA. O 'novo Outlook' do Windows nao deixa"
    Write-Host "      outros programas prepararem emails. E' preciso o Outlook"
    Write-Host "      do Office (no novo Outlook, desligar o separador"
    Write-Host "      'Novo Outlook' para voltar ao classico)."
}

$processo = Get-Process -Name "OUTLOOK" -ErrorAction SilentlyContinue
if ($processo) {
    Write-Host "  Outlook aberto agora: SIM (PID $($processo.Id -join ', '))"
} else {
    Write-Host "  Outlook aberto agora: NAO (convem abri-lo antes de enviar)" -ForegroundColor Yellow
}

# --------------------------------------------------------- prova dos noves
Escrever-Titulo "Prova dos noves - tentar mesmo ligar ao Outlook"

if ($janelaElevada) {
    Write-Host "  SALTADO: esta janela esta' elevada, o resultado nao valeria nada." -ForegroundColor Red
    Write-Host "  Volte a correr o script numa janela normal (ver aviso la' em cima)."
} else {
    try {
        $ol = New-Object -ComObject Outlook.Application
        Write-Host "  LIGOU. Versao do Outlook: $($ol.Version)" -ForegroundColor Green
        Write-Host "  Daqui o Martelo tambem consegue, desde que abra da mesma maneira."
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ol) | Out-Null
    } catch {
        Write-Host "  NAO LIGOU." -ForegroundColor Red
        Write-Host "  $($_.Exception.Message)"
    }
}

Write-Host ""
if ($janelaElevada) {
    Write-Host "ATENCAO: correu como administrador. Repita numa janela normal." -ForegroundColor Red
}
Write-Host "Fim. Tire uma fotografia/print desta janela e envie ao Paulo."
Write-Host ""
Read-Host "Carregue em ENTER para fechar"
