param(
    [switch]$Desktop
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot ".." )).Path
$pythonw = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"

if (-not (Test-Path -LiteralPath $pythonw)) {
    throw "Nao encontrei o ambiente virtual do V3 em: $pythonw"
}

$shell = New-Object -ComObject WScript.Shell
$startMenu = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
$shortcutPath = Join-Path $startMenu "Martelo_Orcamentos_V3.lnk"

function New-MarteloShortcut([string]$Path) {
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $pythonw
    $shortcut.Arguments = "-m app.main"
    $shortcut.WorkingDirectory = $projectRoot
    $shortcut.Description = "Martelo Orçamentos V3"
    $shortcut.WindowStyle = 1
    $shortcut.IconLocation = "$pythonw,0"
    $shortcut.Save()
}

New-MarteloShortcut $shortcutPath
Write-Host "Atalho criado no menu Iniciar: $shortcutPath"

if ($Desktop) {
    $desktopPath = Join-Path ([Environment]::GetFolderPath("Desktop")) "Martelo_Orcamentos_V3.lnk"
    New-MarteloShortcut $desktopPath
    Write-Host "Atalho criado no Ambiente de Trabalho: $desktopPath"
}
