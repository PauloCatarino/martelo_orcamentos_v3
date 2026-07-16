"""Ponto de entrada do executavel (PyInstaller).

Mantido separado de app/main.py para o empacotamento: o PyInstaller aponta
para este ficheiro, que arranca a aplicacao normal.
"""

import sys

from app.main import main

if __name__ == "__main__":
    sys.exit(main())
