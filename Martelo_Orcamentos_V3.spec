# -*- mode: python ; coding: utf-8 -*-
"""Empacotamento do Martelo Orcamentos V3 com PyInstaller.

Perfis (variavel de ambiente MARTELO_BUILD_PROFILE):
  lean (por omissao) -- SEM a pesquisa por IA (torch/sentence-transformers).
                        Executavel muito mais pequeno e rapido de gerar.
  full               -- inclui tudo, incluindo o ML da pesquisa por IA.

A pesquisa por IA e' importada preguicosamente na app, por isso no perfil
lean tudo o resto funciona; so' essa funcionalidade fica indisponivel.
"""

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

ROOT = Path(".").resolve()
ICON = ROOT / "icons" / "martelo.ico"
BUILD_PROFILE = os.getenv("MARTELO_BUILD_PROFILE", "lean").strip().lower() or "lean"

if BUILD_PROFILE not in {"full", "lean"}:
    raise ValueError(f"Perfil de build invalido: {BUILD_PROFILE}")

# --- Ficheiros de dados a incluir ---
datas = []

assets_dir = ROOT / "app" / "ui" / "assets"
if assets_dir.exists():
    datas.append((str(assets_dir), "app/ui/assets"))

icons_dir = ROOT / "icons"
if icons_dir.exists():
    datas.append((str(icons_dir), "icons"))

# ReportLab precisa dos seus ficheiros de dados/fontes.
datas += collect_data_files("reportlab")

hiddenimports = [
    "pymysql",
    "passlib.handlers.bcrypt",
    "win32com.client",
    "pythoncom",
    "pywintypes",
    "win32clipboard",
    "win32con",
    "win32gui",
    "win32process",
    "pywinauto",
    "pywinauto.application",
    "pywinauto.mouse",
    "pywinauto.controls.uia_controls",
    "pywinauto.controls.win32_controls",
    "comtypes",
    "PySide6.QtPdf",
    "PySide6.QtUiTools",
    "pypdf",
]

excludes = [
    "_pytest",
    "pytest",
    "PySide6.scripts.deploy_lib",
    "MySQLdb",
    "psycopg2",
    "tensorboard",
]

if BUILD_PROFILE == "lean":
    excludes += [
        "faiss",
        "sentence_transformers",
        "transformers",
        "tokenizers",
        "safetensors",
        "torch",
        "sklearn",
        "scipy",
        "huggingface_hub",
    ]


a = Analysis(
    [str(ROOT / "run_app.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Martelo_Orcamentos_V3",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ICON)] if ICON.exists() else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Martelo_Orcamentos_V3",
)
