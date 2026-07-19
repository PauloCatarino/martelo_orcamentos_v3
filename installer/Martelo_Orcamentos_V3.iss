; Inno Setup - Martelo Orcamentos V3 (beta)
; Requisitos:
;   1) Gerar o build PyInstaller primeiro (build_beta.py) -> dist\Martelo_Orcamentos_V3\
;   2) Compilar este .iss (ISCC.exe), normalmente via build_beta.py --installer
;
; A versao e a password (opcional) sao passadas na linha de comando:
;   ISCC.exe Martelo_Orcamentos_V3.iss /DAppVersion=0.9.0-beta
;   ISCC.exe Martelo_Orcamentos_V3.iss /DAppVersion=0.9.0-beta /DSetupPassword=xxxx

#define AppName "Martelo Orcamentos V3"
#define AppExeName "Martelo_Orcamentos_V3.exe"

#ifndef AppVersion
  #define AppVersion "0.9.0-beta"
#endif

; Password do instalador: opcional. Definir via /DSetupPassword=... ou a
; variavel de ambiente MARTELO_SETUP_PASSWORD. Se vazia, o instalador nao
; pede password.
#ifndef SetupPassword
  #define SetupPassword GetEnv('MARTELO_SETUP_PASSWORD')
#endif

[Setup]
AppId={{7C2E9A14-5B3D-4F86-9E2A-1D7B4C8F0A93}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Lanca Encanto

DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

OutputDir=Output
OutputBaseFilename=Setup_Martelo_V3_{#AppVersion}

Compression=lzma2
SolidCompression=yes
WizardStyle=modern

#if FileExists("..\icons\icon_le.ico")
SetupIconFile=..\icons\icon_le.ico
#endif
UninstallDisplayIcon={app}\{#AppExeName}

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

#if SetupPassword != ""
Password={#SetupPassword}
Encryption=yes
#endif

[Languages]
Name: "portuguese"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho no Ambiente de Trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
; Binarios e dependencias do PyInstaller (menos o .env, tratado a` parte)
Source: "..\dist\Martelo_Orcamentos_V3\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: ".env;*.log"

; .env - instalar apenas se nao existir, para nao apagar ajustes locais
#if FileExists("..\dist\Martelo_Orcamentos_V3\.env")
Source: "..\dist\Martelo_Orcamentos_V3\.env"; DestDir: "{app}"; Flags: onlyifdoesntexist
#endif

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"
