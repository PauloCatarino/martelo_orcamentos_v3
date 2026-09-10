"""Gera o Excel dos catálogos a partir da base ``martelo_catalogos``.

    python -m scripts.exportar_catalogos
    python -m scripts.exportar_catalogos --destino C:\\temp\\catalogos.xlsx

Sem ``--destino``, grava em ``_gerado/12_Placas_Referencias_GERADO.xlsx``,
dentro da pasta dos catálogos configurada nas Definições. Substitui o ficheiro
gerado da vez anterior e **não toca no ficheiro de origem**.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.db.session import SessionLocal
from app.services.catalogos import exportador
from app.services.system_setting_service import SystemSettingService


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destino",
        default=None,
        help="caminho do .xlsx a escrever (por omissão, _gerado/ na pasta dos catálogos)",
    )
    args = parser.parse_args(argv)

    with SessionLocal() as session:
        destino = args.destino
        if not destino:
            pasta = (
                SystemSettingService(session).obter_valor(
                    "pasta_pesquisa_profunda_ia", ""
                )
                or ""
            ).strip()
            if not pasta:
                print(
                    "ERRO: a 'Pasta Pesquisa Profunda IA' nao esta configurada e "
                    "nao foi dado --destino."
                )
                return 2
            destino = exportador.caminho_por_omissao(pasta)

        print(f"A escrever: {destino}")
        resultado = exportador.exportar(session, destino)

    print(
        f"OK - {resultado.separadores} separadores, {resultado.referencias} "
        f"referencias, {resultado.precos} precos."
    )
    print(f"Ficheiro: {resultado.caminho}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    try:
        sys.exit(main())
    except RuntimeError as erro:
        print(f"ERRO: {erro}")
        sys.exit(2)
