"""Gerar o executavel (e, opcionalmente, o instalador) do Martelo V3.

Passos:
  1. PyInstaller empacota a app  ->  dist\\Martelo_Orcamentos_V3\\
  2. Copia o .env escolhido (servidor e base, SEM credenciais) para junto do .exe
  3. (--installer) Inno Setup gera  installer\\Output\\Setup_Martelo_V3_<versao>.exe

Uso:
    .venv\\Scripts\\python.exe build_beta.py --producao --installer  # VERSAO OFICIAL
    .venv\\Scripts\\python.exe build_beta.py --installer             # beta (testes)
    .venv\\Scripts\\python.exe build_beta.py --profile full          # inclui a IA (grande)

O que muda entre oficial e beta e' SO' o ficheiro .env que vai dentro do
instalador -- `deploy\\.env.producao` (base oficial, sem rotulo na janela) ou
`deploy\\.env.beta` (base de testes). O executavel e' exatamente o mesmo.

Pre-requisitos:
  - PyInstaller instalado no .venv
  - deploy\\.env.producao (ou deploy\\.env.beta) criado a partir do .exemplo ao
    lado; nao leva credenciais nenhumas -- cada pessoa entra com a sua conta
  - Para --installer: Inno Setup 6 (ISCC.exe)
"""

from __future__ import annotations

import argparse
import getpass
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "Martelo_Orcamentos_V3"
ENV_BETA = ROOT / "deploy" / ".env.beta"
ENV_PRODUCAO = ROOT / "deploy" / ".env.producao"
SPEC = ROOT / "Martelo_Orcamentos_V3.spec"
ISS = ROOT / "installer" / "Martelo_Orcamentos_V3.iss"

ISCC_CANDIDATOS = [
    Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
    Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
]


def _versao() -> str:
    sys.path.insert(0, str(ROOT))
    from version import version_completa  # noqa: E402
    return version_completa()


def _ler_env(caminho: Path) -> dict[str, str]:
    dados: dict[str, str] = {}
    for linha in caminho.read_text(encoding="utf-8", errors="replace").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            k, _, v = linha.partition("=")
            dados[k.strip()] = v.strip()
    return dados


def _verificar_env(env_origem: Path) -> None:
    """Confirma que o .env escolhido chega mesmo ao servidor ANTES de construir.

    Fail-fast: evita gastar minutos a gerar um instalador que nao conecta.

    O ficheiro ja' nao leva credenciais -- cada pessoa entra com a sua conta --
    por isso a prova de ligacao pede-as aqui, a quem esta' a fazer o build. Se
    for para saltar (build sem servidor a` mao), responda em branco.
    """
    print(f"[0/3] verificar {env_origem}")
    if not env_origem.exists():
        raise SystemExit(
            f"[ERRO] falta {env_origem}.\n"
            f"       Copie {env_origem}.exemplo para {env_origem.name}."
        )

    env = _ler_env(env_origem)
    for chave in ("DB_USER", "DB_PASSWORD"):
        if env.get(chave):
            raise SystemExit(
                f"[ERRO] o {env_origem} tem {chave} preenchido.\n"
                "       Este ficheiro vai para o PC de toda a gente e NAO pode\n"
                "       levar credenciais: cada pessoa entra com a sua conta.\n"
                "       Apague a linha e volte a correr o build."
            )

    for chave in ("DB_HOST", "DB_NAME"):
        if not env.get(chave):
            raise SystemExit(f"[ERRO] falta {chave} em {env_origem}.")

    base = f"{env.get('DB_NAME')} @ {env.get('DB_HOST')}"
    print(f"      sem credenciais do Martelo (bem) -> {base}")

    # O Arquivo V2 e' o unico sitio onde ainda ha' uma conta partilhada. E' a
    # MESMA conta com que o Martelo V2 trabalha, por isso nao se lhe pode tirar
    # a escrita -- ja' se tentou e parou o V2 em todos os PCs. A saida certa e'
    # dar ao V3 uma conta propria e so'-leitura para consultar o arquivo (ver a
    # seccao 8 do deploy/mysql_contas_beta.sql).
    if env.get("V2_DB_PASSWORD"):
        print(
            f"      AVISO: leva as credenciais do Arquivo V2 ({env.get('V2_DB_USER')}),"
            " que sao as\n             mesmas do Martelo V2 e dao acesso total a"
            " essa base."
        )

    utilizador = input("      utilizador para testar a ligacao (ENTER salta): ").strip()
    if not utilizador:
        print("      AVISO: ligacao nao testada.")
        return

    password = getpass.getpass("      password: ")
    try:
        import pymysql
        con = pymysql.connect(
            host=env.get("DB_HOST", "127.0.0.1"),
            port=int(env.get("DB_PORT", "3306")),
            user=utilizador,
            password=password,
            database=env.get("DB_NAME", ""),
            connect_timeout=6,
        )
        con.close()
    except Exception as e:  # noqa: BLE001
        raise SystemExit(
            f"[ERRO] nao liga a` base de dados: {e}\n"
            f"       Confirme DB_HOST={env.get('DB_HOST')}, "
            f"DB_NAME={env.get('DB_NAME')} e as credenciais que escreveu."
        )
    print(f"      OK -> {utilizador} liga a {base}")


LOG = ROOT / "build_last.log"


def _pyinstaller(profile: str) -> None:
    print(f"[1/3] PyInstaller (perfil {profile})... isto pode demorar varios minutos.")
    print(f"      (log completo em {LOG.name})")
    env = dict(os.environ)
    env["MARTELO_BUILD_PROFILE"] = profile
    for pasta in (ROOT / "build", DIST.parent):
        if pasta.exists():
            try:
                shutil.rmtree(pasta)
            except OSError as e:
                raise SystemExit(
                    f"[ERRO] nao consegui limpar {pasta}: {e}\n"
                    "       Feche o Explorador de Ficheiros e outras janelas abertas "
                    "nessa pasta e tente de novo."
                )
    # Grava o output todo num ficheiro E mostra no ecra ao mesmo tempo.
    with LOG.open("w", encoding="utf-8", errors="replace") as log:
        proc = subprocess.Popen(
            [sys.executable, "-m", "PyInstaller", "--noconfirm", str(SPEC)],
            cwd=str(ROOT), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        for linha in proc.stdout:
            log.write(linha)
            if any(p in linha for p in ("ERROR", "WARNING", "Traceback", "Build complete")):
                print("      " + linha.rstrip())
        rc = proc.wait()

    if rc != 0:
        print("\n----- fim do log do PyInstaller (erro real) -----")
        for linha in LOG.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]:
            print("  " + linha)
        raise SystemExit(f"\n[ERRO] PyInstaller falhou (codigo {rc}). Log completo: {LOG}")
    if not (DIST / "Martelo_Orcamentos_V3.exe").exists():
        raise SystemExit("[ERRO] o .exe nao foi gerado.")
    print(f"      OK -> {DIST}")


def _copiar_env(env_origem: Path) -> None:
    print(f"[2/3] copiar {env_origem.name} para junto do .exe")
    if not env_origem.exists():
        raise SystemExit(
            f"[ERRO] falta {env_origem}.\n"
            f"       Copie {env_origem}.exemplo para {env_origem.name}."
        )

    # Ultima barreira antes de o ficheiro ir para o PC de toda a gente: mesmo
    # que alguem tenha acrescentado credenciais depois da verificacao inicial,
    # nao passam daqui.
    env = _ler_env(env_origem)
    if env.get("DB_USER") or env.get("DB_PASSWORD"):
        raise SystemExit(
            f"[ERRO] o {env_origem} tem credenciais e ia para todos os PCs.\n"
            "       Apague DB_USER/DB_PASSWORD antes de construir."
        )

    shutil.copy2(env_origem, DIST / ".env")
    print(f"      OK (sem credenciais) -> {DIST / '.env'}")


def _instalador(versao: str) -> None:
    print("[3/3] Inno Setup (instalador)")
    iscc = next((c for c in ISCC_CANDIDATOS if c.exists()), None)
    if iscc is None:
        raise SystemExit("[ERRO] ISCC.exe (Inno Setup 6) nao encontrado.")
    res = subprocess.run(
        [str(iscc), f"/DAppVersion={versao}", str(ISS)],
        cwd=str(ISS.parent),
    )
    if res.returncode != 0:
        raise SystemExit("[ERRO] Inno Setup falhou.")
    print(f"      OK -> installer\\Output\\Setup_Martelo_V3_{versao}.exe")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--installer", action="store_true", help="tambem gerar o instalador")
    ap.add_argument("--profile", choices=["lean", "full"], default="lean")
    ap.add_argument(
        "--producao",
        action="store_true",
        help="versao OFICIAL: leva o deploy\\.env.producao (base oficial) "
             "em vez do .env.beta",
    )
    args = ap.parse_args()

    env_origem = ENV_PRODUCAO if args.producao else ENV_BETA
    destino = "OFICIAL" if args.producao else "beta (testes)"

    versao = _versao()
    print(f"Martelo V3  versao {versao}  [{destino}]  (perfil {args.profile})")
    print(f"  configuracao: {env_origem.name}\n")
    _verificar_env(env_origem)
    _pyinstaller(args.profile)
    _copiar_env(env_origem)
    if args.installer:
        _instalador(versao)
    print("\nConcluido.")


if __name__ == "__main__":
    main()
