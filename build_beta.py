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
    _pyinstaller(args.profile)
    _copiar_env()
    if args.installer:
        _instalador(versao)
    print("\nConcluido.")


if __name__ == "__main__":
    main()
