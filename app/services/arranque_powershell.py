"""Arrancar o PowerShell a partir do Martelo: todos os sítios passam por aqui.

19-11-2026, obras 1912 e _330 no PC do Paulo (Martelo 1.0.34 instalado): o
Windows recusou várias vezes arrancar o PowerShell (``[WinError 5] Acesso
negado`` no próprio ``CreateProcess``), umas vezes sim, outras não, a segundos
de distância. Nada nos registos do Windows Defender, da integridade do código
nem do AppLocker; do ``python.exe`` as mesmas chamadas passaram 20 em 20. É o
padrão de um antivírus (neste PC, o Kaspersky) a travar o
``Martelo_Orcamentos_V3.exe`` quando ele lança o PowerShell.

Por isso, aqui:

- o ``powershell.exe`` vai pelo caminho completo da pasta do Windows: sem
  procurar antes na pasta do Martelo e na pasta atual, onde um
  ``powershell.exe`` qualquer passava à frente do verdadeiro;
- se o Windows recusar o arranque, tenta-se mais duas vezes. O processo não
  chegou a nascer, por isso repetir não faz nada duas vezes (nem nas escritas
  no iMos);
- se continuar a recusar, a mensagem diz o que fazer, em vez de só «Acesso
  negado».
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Callable, Sequence

#: Quantas vezes se tenta arrancar o PowerShell antes de desistir.
TENTATIVAS = 3
#: Espera (segundos) antes da 2.ª e da 3.ª tentativa.
PAUSAS_SEGUNDOS = (1.0, 2.0)
#: ``ERROR_ACCESS_DENIED`` do Windows.
_ACESSO_NEGADO = 5

MENSAGEM_RECUSADO = (
    "O Windows não deixou o Martelo arrancar o PowerShell (Acesso negado), "
    "nem à {tentativas}.ª tentativa. O Martelo usa-o para ler o iMos e o PHC e "
    "para preparar o Excel.\n\n"
    "Costuma ser o antivírus (Kaspersky) a travar o Martelo. Abra o Kaspersky › "
    "Relatórios e procure o Martelo_Orcamentos_V3.exe: se lá estiver, o Martelo "
    "tem de passar a aplicação fidedigna no antivírus. Entretanto, pode tentar "
    "outra vez daqui a uns segundos."
)


class PowerShellRecusado(PermissionError):
    """O Windows recusou arrancar o PowerShell em todas as tentativas."""


def caminho_powershell() -> str:
    """O ``powershell.exe`` da pasta do Windows (ou ``powershell`` se não existir)."""
    raiz = os.environ.get("SystemRoot") or os.environ.get("windir") or ""
    if raiz:
        caminho = Path(raiz) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
        if caminho.is_file():
            return str(caminho)
    return "powershell"


def _acesso_negado(erro: OSError) -> bool:
    return getattr(erro, "winerror", None) == _ACESSO_NEGADO


def arrancar_powershell(
    argumentos: Sequence[str],
    *,
    dormir: Callable[[float], None] | None = None,
    **opcoes,
) -> subprocess.CompletedProcess:
    """``subprocess.run`` do PowerShell com ``argumentos`` (sem o executável).

    As ``opcoes`` seguem tal e qual para o ``subprocess.run``. Só se repete
    quando o Windows recusa ARRANCAR o processo; um PowerShell que arranca e
    falha devolve o código de saída como sempre.
    """
    dormir = dormir or time.sleep
    comando = [caminho_powershell(), *argumentos]
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            return subprocess.run(comando, **opcoes)
        except PermissionError as erro:
            if not _acesso_negado(erro):
                raise
            if tentativa == TENTATIVAS:
                raise PowerShellRecusado(
                    MENSAGEM_RECUSADO.format(tentativas=TENTATIVAS)
                ) from erro
            dormir(PAUSAS_SEGUNDOS[min(tentativa, len(PAUSAS_SEGUNDOS)) - 1])
    raise AssertionError("inalcançável")  # pragma: no cover
