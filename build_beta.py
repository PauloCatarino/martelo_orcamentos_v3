"""Gerar o executavel (e, opcionalmente, o instalador) do beta do Martelo V3.

Passos:
  1. PyInstaller empacota a app  ->  dist\\Martelo_Orcamentos_V3\\
  2. Copia deploy\\.env.beta (com a password do servidor) para junto do .exe
  3. (--installer) Inno Setup gera  installer\\Output\\Setup_Martelo_V3_<versao>.exe

Uso:
    .venv\\Scripts\\python.exe build_beta.py               # so' o executavel
    .venv\\Scripts\\python.exe build_beta.py --installer    # + instalador
    .venv\\Scripts\\python.exe build_beta.py --profile full # inclui a IA (grande)

Pre-requisitos:
  - PyInstaller instalado no .venv
  - deploy\\.env.beta preenchido (copiar de deploy\\.env.beta.exemplo)
  - Para --installer: Inno Setup 6 (ISCC.exe)
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist" / "Martelo_Orcamentos_V3"
ENV_ORIGEM = ROOT / "deploy" / ".env.beta"
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


def _verificar_env() -> None:
    """Confirma que deploy/.env.beta liga mesmo a` base de dados ANTES de construir.

    Fail-fast: evita gastar minutos a gerar um instalador que nao conecta.
    """
    print("[0/3] verificar deploy/.env.beta")
    if not ENV_ORIGEM.exists():
        raise SystemExit(
            f"[ERRO] falta {ENV_ORIGEM}.\n"
            "       Copie deploy\\.env.beta.exemplo para deploy\\.env.beta e "
            "preencha a DB_PASSWORD."
        )
    env = _ler_env(ENV_ORIGEM)
    if env.get("DB_PASSWORD", "") in ("", "POR_DEFINIR"):
        raise SystemExit(
            f"[ERRO] a DB_PASSWORD em {ENV_ORIGEM} ainda esta por preencher "
            "(POR_DEFINIR).\n"
            "       Abra o ficheiro no VS Code, ponha a password do utilizador "
            "martelo_v3 e GRAVE (Ctrl+S)."
        )
    try:
        import pymysql
        con = pymysql.connect(
            host=env.get("DB_HOST", "127.0.0.1"),
            port=int(env.get("DB_PORT", "3306")),
            user=env.get("DB_USER", ""),
            password=env.get("DB_PASSWORD", ""),
            database=env.get("DB_NAME", ""),
            connect_timeout=6,
        )
        con.close()
    except Exception as e:  # noqa: BLE001
        raise SystemExit(
            f"[ERRO] o .env.beta nao liga a` base de dados: {e}\n"
            f"       Confirme DB_HOST={env.get('DB_HOST')}, "
            f"DB_NAME={env.get('DB_NAME')}, DB_USER={env.get('DB_USER')} e a password."
        )
    print(f"      OK -> liga a {env.get('DB_NAME')} @ {env.get('DB_HOST')}")


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


def _copiar_env() -> None:
    print("[2/3] copiar .env do beta")
    if not ENV_ORIGEM.exists():
        raise SystemExit(
            f"[ERRO] falta {ENV_ORIGEM}.\n"
            "       Copie deploy\\.env.beta.exemplo para deploy\\.env.beta e "
            "preencha a DB_PASSWORD."
        )
    shutil.copy2(ENV_ORIGEM, DIST / ".env")
    print(f"      OK -> {DIST / '.env'}")


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
    args = ap.parse_args()

    versao = _versao()
    print(f"Martelo V3  versao {versao}  (perfil {args.profile})\n")
    _verificar_env()
    _pyinstaller(args.profile)
    _copiar_env()
    if args.installer:
        _instalador(versao)
    print("\nConcluido.")


if __name__ == "__main__":
    main()
