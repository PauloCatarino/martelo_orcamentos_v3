"""Module image helpers (phase 8U.4).

Copy a chosen image into the configured "Pasta de Imagens de Módulos" using a
filename based on the module code, and build a file:// URL / HTML tooltip to
preview the image (zoom on hover). All operations are defensive: on any problem
they keep the original path and return a friendly warning instead of raising.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class ResultadoImagem:
    """Outcome of copying a module image: final path + optional warning."""

    caminho: str | None
    aviso: str | None = None


def sanitizar_codigo(codigo: str | None) -> str:
    """Return a filesystem-safe base name from a module code.

    Keeps letters/digits/underscore/hyphen; every other character becomes '_'.
    """
    texto = (codigo or "").strip()
    seguro = "".join(c if (c.isalnum() or c in "_-") else "_" for c in texto)
    seguro = seguro.strip("_")
    return seguro or "modulo"


def copiar_imagem_para_pasta(
    origem: str | None, pasta: str | None, codigo: str
) -> ResultadoImagem:
    """Copy ``origem`` into ``pasta`` as ``<codigo>.<ext>``; return the new path.

    - No image chosen -> (None, None).
    - No folder configured -> keep the original path with a gentle warning.
    - Source missing / copy fails -> keep the original path with a warning.
    - Source already at the destination -> reuse it (no copy).
    """
    if not origem or not origem.strip():
        return ResultadoImagem(caminho=None, aviso=None)

    origem = origem.strip()

    if not pasta or not pasta.strip():
        return ResultadoImagem(
            caminho=origem,
            aviso=(
                "Pasta de imagens de módulos não configurada (Configurações → "
                "Caminhos do Sistema); mantido o caminho original da imagem."
            ),
        )

    pasta = pasta.strip()

    if not os.path.isfile(origem):
        return ResultadoImagem(
            caminho=origem,
            aviso=f"Imagem '{origem}' não encontrada; mantido o caminho original.",
        )

    extensao = os.path.splitext(origem)[1].lower() or ".png"
    destino = os.path.join(pasta, f"{sanitizar_codigo(codigo)}{extensao}")

    try:
        os.makedirs(pasta, exist_ok=True)
        if os.path.abspath(origem) != os.path.abspath(destino):
            shutil.copy2(origem, destino)
    except OSError as error:
        return ResultadoImagem(
            caminho=origem,
            aviso=(
                "Não foi possível copiar a imagem para a pasta de módulos "
                f"({error}); mantido o caminho original."
            ),
        )

    return ResultadoImagem(caminho=destino, aviso=None)


def caminho_para_file_url(caminho: str | None) -> str:
    """Convert a filesystem path to a file:// URL (handles Windows backslashes)."""
    if not caminho:
        return ""

    normalizado = caminho.replace("\\", "/")
    if normalizado.startswith("//"):
        # UNC path: //server/share/... -> file://server/share/...
        return "file:" + normalizado
    return "file:///" + normalizado.lstrip("/")


def tooltip_imagem_html(caminho: str | None, largura: int = 320) -> str:
    """Build an HTML <img> tooltip showing the image enlarged (zoom on hover)."""
    if not caminho:
        return ""
    url = caminho_para_file_url(caminho)
    return f'<img src="{url}" width="{largura}">'
