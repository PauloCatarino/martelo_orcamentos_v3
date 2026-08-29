"""Subir o numero da versao do Martelo, antes de gerar um instalador novo.

PORQUE E' QUE ISTO EXISTE
-------------------------
O numero da versao e' a UNICA forma de saber o que e' que cada colega tem
instalado. Se sairem dois instaladores diferentes com o mesmo numero, deixa de
haver maneira de responder a "ele ja' tem a correcao ou nao?" -- e um dia
alguem vai jurar que atualizou quando nao atualizou.

Por isso: **um numero novo para cada instalador que sai daqui.**

COMO SE USA
-----------
    .venv\\Scripts\\python.exe scripts\\nova_versao.py

Sobe o ultimo numero (1.0.0 -> 1.0.1). E' o que se quer quase sempre: uma
correcao, uma melhoria, mais um instalador.

    .venv\\Scripts\\python.exe scripts\\nova_versao.py 1.1.0

Escolhe o numero a` mao. Serve para quando entra uma funcionalidade grande
(sobe o do meio) ou uma mudanca de fundo (sobe o primeiro).

O QUE MUDA
----------
Uma linha, em app/config/versao.py. Mais nada -- o instalador, o diario de
bordo e o "Reportar problema" vao todos beber a esse sitio.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FICHEIRO = RAIZ / "app" / "config" / "versao.py"

PADRAO = re.compile(r'^APP_VERSION = "(\d+\.\d+\.\d+)"$', re.MULTILINE)


def ler_versao(texto: str) -> str:
    """O numero que esta' la' agora."""
    encontrado = PADRAO.search(texto)
    if not encontrado:
        raise ValueError(
            "Nao encontrei a linha APP_VERSION em app/config/versao.py. "
            "Alguem mudou o formato do ficheiro?"
        )
    return encontrado.group(1)


def proxima_versao(atual: str) -> str:
    """1.0.0 -> 1.0.1. Sobe so' o ultimo numero."""
    maior, medio, menor = (int(parte) for parte in atual.split("."))
    return f"{maior}.{medio}.{menor + 1}"


def validar(nova: str) -> str:
    if not re.fullmatch(r"\d+\.\d+\.\d+", nova):
        raise ValueError(
            f"'{nova}' nao serve como versao. Tem de ser tres numeros "
            "separados por pontos, por exemplo 1.0.1 ou 1.2.0."
        )
    return nova


def e_maior(nova: str, atual: str) -> bool:
    """Impede descer sem dar por isso (1.0.5 -> 1.0.2 seria um erro grave)."""
    return tuple(int(p) for p in nova.split(".")) > tuple(
        int(p) for p in atual.split(".")
    )


def aplicar(texto: str, nova: str) -> str:
    return PADRAO.sub(f'APP_VERSION = "{nova}"', texto, count=1)


def main() -> None:
    texto = FICHEIRO.read_text(encoding="utf-8")
    atual = ler_versao(texto)

    if len(sys.argv) > 1:
        nova = validar(sys.argv[1].strip())
        if not e_maior(nova, atual):
            raise SystemExit(
                f"[ERRO] a versao {nova} nao e' maior do que a atual ({atual}).\n"
                "       Um numero novo tem de subir, nunca descer: senao dois\n"
                "       instaladores diferentes ficavam com o mesmo nome."
            )
    else:
        nova = proxima_versao(atual)

    FICHEIRO.write_text(aplicar(texto, nova), encoding="utf-8")

    print(f"Versao {atual}  ->  {nova}")
    print()
    print("A seguir:")
    print("  1. .venv\\Scripts\\python.exe -m pytest -q")
    print("  2. git add -A  &&  git commit  &&  git push")
    print("  3. .venv\\Scripts\\python.exe build_beta.py --producao "
          "--installer --profile full")
    print()
    print(f"   Sai:  installer\\Output\\Setup_Martelo_V3_{nova}.exe")


if __name__ == "__main__":
    main()
