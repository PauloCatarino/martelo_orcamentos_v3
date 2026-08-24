"""Where the photos of a ticket live, and how they get there.

As fotos ficam na pasta da obra, em ``…\\Ocorrencias\\T0007\\`` — quem abre a
pasta da obra no explorador vê-as sem precisar do programa, e o backup do
servidor já as apanha.

Como o ``modulo_imagem`` (de onde este módulo é decalcado), nada aqui levanta
exceção: uma foto é sempre acessória, e a rede em baixo não pode impedir que o
ticket seja escrito. Todos os problemas voltam como aviso.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.domain.ocorrencia_tipos import pasta_ticket as _nome_pasta_ticket


#: Subpasta criada dentro da pasta da obra.
SUBPASTA_OCORRENCIAS = "Ocorrencias"

EXTENSOES_IMAGEM = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"}
)

#: Anexos que não são fotos mas que também se veem em miniatura (a primeira
#: página serve de pré-visualização, como nas imagens).
EXTENSOES_PDF = frozenset({".pdf"})


@dataclass(frozen=True)
class ResultadoAnexo:
    """Outcome of attaching one file: final path + optional warning."""

    caminho: str | None
    nome_original: str | None = None
    aviso: str | None = None


def pasta_anexos_ticket(pasta_obra: str | Path | None, numero: int | None) -> Path | None:
    """Return ``<pasta da obra>/Ocorrencias/T0007`` — None if there is no folder."""
    if not pasta_obra or not str(pasta_obra).strip():
        return None
    return Path(str(pasta_obra).strip()) / SUBPASTA_OCORRENCIAS / _nome_pasta_ticket(numero)


def preparar_pasta(pasta: Path | None) -> tuple[Path | None, str | None]:
    """Create the ticket folder; return (path, warning)."""
    if pasta is None:
        return None, (
            "Esta obra ainda não tem pasta no servidor; as fotos não podem ser "
            "guardadas junto da obra."
        )
    try:
        pasta.mkdir(parents=True, exist_ok=True)
    except OSError as erro:
        return None, f"Não foi possível criar a pasta das fotos ({erro})."
    return pasta, None


def e_imagem(caminho: str | Path | None) -> bool:
    """True when the file looks like a picture (by extension)."""
    if not caminho:
        return False
    return Path(str(caminho)).suffix.lower() in EXTENSOES_IMAGEM


def e_pdf(caminho: str | Path | None) -> bool:
    """True when the file is a PDF (by extension)."""
    if not caminho:
        return False
    return Path(str(caminho)).suffix.lower() in EXTENSOES_PDF


def proximo_caminho(pasta: Path, numero: int | None, extensao: str) -> Path:
    """Return the next free ``T0007_03.png`` inside the ticket folder.

    Conta os que já lá estão em vez de confiar no número de anexos na base de
    dados: se alguém apagar um ficheiro à mão, o nome seguinte não colide.
    """
    base = _nome_pasta_ticket(numero)
    sufixo = extensao if extensao.startswith(".") else f".{extensao}"
    sufixo = sufixo.lower() or ".png"

    indice = 1
    while indice < 1000:
        candidato = pasta / f"{base}_{indice:02d}{sufixo}"
        if not candidato.exists():
            return candidato
        indice += 1
    return pasta / f"{base}_{indice:02d}{sufixo}"


def copiar_anexo(
    origem: str | Path | None, pasta: Path | None, numero: int | None
) -> ResultadoAnexo:
    """Copy ``origem`` into the ticket folder; never raises."""
    if not origem or not str(origem).strip():
        return ResultadoAnexo(caminho=None, aviso=None)

    caminho_origem = Path(str(origem).strip())
    nome_original = caminho_origem.name

    if not caminho_origem.is_file():
        return ResultadoAnexo(
            caminho=None,
            nome_original=nome_original,
            aviso=f"Ficheiro '{nome_original}' não encontrado.",
        )

    destino_pasta, aviso = preparar_pasta(pasta)
    if destino_pasta is None:
        return ResultadoAnexo(caminho=None, nome_original=nome_original, aviso=aviso)

    destino = proximo_caminho(destino_pasta, numero, caminho_origem.suffix)
    try:
        if os.path.abspath(caminho_origem) == os.path.abspath(destino):
            return ResultadoAnexo(caminho=str(destino), nome_original=nome_original)
        shutil.copy2(caminho_origem, destino)
    except OSError as erro:
        return ResultadoAnexo(
            caminho=None,
            nome_original=nome_original,
            aviso=f"Não foi possível copiar '{nome_original}' ({erro}).",
        )

    return ResultadoAnexo(caminho=str(destino), nome_original=nome_original)


def existe(caminho: str | Path | None) -> bool:
    """True when the attachment is still on disk (network folders go away)."""
    if not caminho:
        return False
    try:
        return Path(str(caminho)).is_file()
    except OSError:
        return False
