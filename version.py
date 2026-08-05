"""Versao da aplicacao Martelo Orcamentos V3 — reexportada para o empacotamento.

**O numero NAO se edita aqui: edita-se em `app/config/versao.py`.**

Este ficheiro existe porque o `build_beta.py` e o instalador o procuram na raiz
desde o inicio. O numero em si vive dentro do pacote da aplicacao, para o
executavel o encontrar pelo caminho da app — e para haver um so' numero, o
mesmo no instalador, no diario de bordo e no "Reportar problema".
"""

from __future__ import annotations

from app.config.versao import APP_STAGE, APP_VERSION, version_completa

__all__ = ["APP_STAGE", "APP_VERSION", "version_completa"]
