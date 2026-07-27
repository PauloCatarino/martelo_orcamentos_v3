"""Leitura do catálogo de guias locais do Centro de Ajuda.

Os guias vivem em ``app/ui/assets/ajuda`` para que texto, imagens e áudio
possam ser alterados sem mexer no leitor Qt. O ficheiro JSON é incluído no
executável pelo ``.spec`` juntamente com os restantes assets da interface.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "ajuda"
_CATALOGO_PATH = _ASSETS_DIR / "guias.json"


@dataclass(frozen=True)
class FalaNarrador:
    """Uma fala curta que é simultaneamente narração e transcrição."""

    narrador: str
    texto: str


@dataclass(frozen=True)
class PassoGuia:
    """Um diapositivo de um guia de ajuda."""

    titulo: str
    explicacao: str
    imagem: Path
    falas: tuple[FalaNarrador, ...]


@dataclass(frozen=True)
class GuiaAjuda:
    """Guia local, independente da página Qt que o apresenta."""

    id: str
    titulo: str
    resumo: str
    versao: int
    passos: tuple[PassoGuia, ...]


def carregar_guias() -> tuple[GuiaAjuda, ...]:
    """Carrega os guias válidos incluídos com a aplicação.

    Conteúdo inválido não deve impedir o arranque do programa: é ignorado e o
    catálogo mostra simplesmente que não há guia disponível.
    """
    try:
        dados = json.loads(_CATALOGO_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()

    if not isinstance(dados, dict) or dados.get("schema_version") != 1:
        return ()

    guias: list[GuiaAjuda] = []
    for bruto in dados.get("guias", []):
        guia = _ler_guia(bruto)
        if guia is not None:
            guias.append(guia)
    return tuple(guias)


def _ler_guia(bruto: object) -> GuiaAjuda | None:
    if not isinstance(bruto, dict):
        return None
    guia_id = _texto(bruto.get("id"))
    titulo = _texto(bruto.get("titulo"))
    resumo = _texto(bruto.get("resumo"))
    versao = bruto.get("versao")
    if not guia_id or not titulo or not resumo or not isinstance(versao, int):
        return None

    passos: list[PassoGuia] = []
    for bruto_passo in bruto.get("passos", []):
        passo = _ler_passo(bruto_passo)
        if passo is not None:
            passos.append(passo)
    if not passos:
        return None
    return GuiaAjuda(guia_id, titulo, resumo, versao, tuple(passos))


def _ler_passo(bruto: object) -> PassoGuia | None:
    if not isinstance(bruto, dict):
        return None
    titulo = _texto(bruto.get("titulo"))
    explicacao = _texto(bruto.get("explicacao"))
    imagem_relativa = _texto(bruto.get("imagem"))
    if not titulo or not explicacao or not imagem_relativa:
        return None

    falas: list[FalaNarrador] = []
    for fala in bruto.get("falas", []):
        if not isinstance(fala, dict):
            continue
        narrador, texto = _texto(fala.get("narrador")), _texto(fala.get("texto"))
        if narrador and texto:
            falas.append(FalaNarrador(narrador, texto))
    if not falas:
        return None

    return PassoGuia(
        titulo=titulo,
        explicacao=explicacao,
        imagem=_ASSETS_DIR / imagem_relativa,
        falas=tuple(falas),
    )


def _texto(valor: object) -> str:
    return valor.strip() if isinstance(valor, str) else ""
