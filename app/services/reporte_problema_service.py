"""Empacotar um problema do V3 para o Paulo poder perceber o que aconteceu.

A ideia é a dos programas que "enviam o relatório ao fabricante": em vez de
alguém ir buscar o ficheiro de log ao PC do utilizador, o utilizador carrega
num botão e o Martelo junta o contexto (quem, onde, que obra, que versão) às
últimas linhas do diário de bordo num único ficheiro de texto.
"""

from __future__ import annotations

import platform
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Sequence

from sqlalchemy.orm import Session

from app.core import diario_bordo
from app.services.system_setting_service import SystemSettingService

KEY_EMAIL_SUPORTE = "email_suporte_v3"

#: Linhas do diário que acompanham o relatório (chega para reconstituir o dia).
LINHAS_NO_RELATORIO = 400


def email_suporte(session: Session) -> str:
    """Email configurado em Configurações → Caminhos do Sistema."""
    valor = SystemSettingService(session).obter_valor(KEY_EMAIL_SUPORTE, "") or ""
    return valor.strip()


def montar_relatorio(
    descricao: str,
    *,
    versao: str,
    contexto: dict[str, str] | None = None,
    linhas: Sequence[str] | None = None,
    momento: datetime | None = None,
) -> str:
    """Build the text that is sent: context first, diary lines after."""
    contexto = contexto or diario_bordo.contexto_atual()
    linhas = list(
        linhas if linhas is not None else diario_bordo.linhas_recentes(LINHAS_NO_RELATORIO)
    )
    quando = (momento or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    cabecalho = [
        "RELATÓRIO DE PROBLEMA — Martelo Orçamentos V3",
        f"Data: {quando}",
        f"Versão: {versao or '?'}",
        f"Utilizador: {contexto.get('utilizador', '-')}",
        f"Menu: {contexto.get('menu', '-')}",
        f"Obra: {contexto.get('obra', '-')}",
        f"PC: {platform.node()}",
        f"Sistema: {platform.platform()}",
        f"Diário: {diario_bordo.caminho_diario()}",
        "",
        "O QUE O UTILIZADOR ESTAVA A FAZER:",
        (descricao or "").strip() or "(não preenchido)",
        "",
        f"ÚLTIMAS {len(linhas)} LINHAS DO DIÁRIO:",
    ]
    return "\n".join([*cabecalho, *linhas, ""])


def nome_do_relatorio(contexto: dict[str, str] | None = None, momento: datetime | None = None) -> str:
    """File name with user and timestamp, so reports never overwrite each other."""
    contexto = contexto or diario_bordo.contexto_atual()
    utilizador = _seguro(contexto.get("utilizador", "utilizador"))
    carimbo = (momento or datetime.now()).strftime("%Y%m%d_%H%M%S")
    return f"problema_martelo_{utilizador}_{carimbo}.txt"


def gravar_relatorio(
    texto: str,
    *,
    pasta: Path | str | None = None,
    nome: str | None = None,
) -> Path:
    """Write the report to disk (temp folder by default) and return its path."""
    destino_pasta = Path(pasta) if pasta else Path(tempfile.gettempdir())
    destino_pasta.mkdir(parents=True, exist_ok=True)
    destino = destino_pasta / (nome or nome_do_relatorio())
    destino.write_text(texto, encoding="utf-8")
    return destino


def _seguro(valor: str) -> str:
    limpo = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(valor or ""))
    return limpo.strip("_") or "utilizador"
