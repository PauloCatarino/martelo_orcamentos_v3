"""Diário de bordo do Martelo: o que se passou antes de a coisa correr mal.

Até aqui o V3 escrevia o `logging` no terminal — e como o executável é
empacotado sem consola, isso ia tudo para o vazio: quando algo rebentava no PC
de alguém, não ficava rasto nenhum. Este módulo grava num ficheiro **local**
(nunca no servidor: seria lento e ficaria preso) com rotação automática, por
isso o espaço ocupado tem um teto — cinco ficheiros de 2 MB e mais nada.

O que fica registado é: o que o utilizador fez (menu, obra, ações grandes), o
que o Martelo lhe mostrou (avisos e erros) e os erros inesperados com o
traceback completo. Nunca passwords nem ligações à base de dados.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
import threading
from logging.handlers import RotatingFileHandler
from pathlib import Path

NOME_PASTA = "Martelo Orcamentos V3"
NOME_FICHEIRO = "diario_martelo.log"

#: Teto por PC: 2 MB × 5 ficheiros. Um dia normal de trabalho não chega a 50 KB.
MAX_BYTES = 2 * 1024 * 1024
COPIAS = 4

FORMATO = "%(asctime)s | %(levelname)-7s | %(utilizador)s | %(menu)s | %(obra)s | %(message)s"
FORMATO_DATA = "%Y-%m-%d %H:%M:%S"

_LOGGER = logging.getLogger("martelo.diario")

#: Contexto que acompanha cada linha — quem, onde e em que obra.
_CONTEXTO = {"utilizador": "-", "menu": "-", "obra": "-"}

_handler: RotatingFileHandler | None = None


# ---- onde vive o ficheiro ---------------------------------------------------
def caminho_diario() -> Path:
    """Return a writable local path for the diary (never on the server)."""
    explicito = (os.getenv("MARTELO_DIARIO_PATH") or "").strip()
    candidatos: list[Path] = []
    if explicito:
        candidatos.append(Path(explicito).expanduser())

    localappdata = (os.getenv("LOCALAPPDATA") or "").strip()
    if localappdata:
        candidatos.append(Path(localappdata) / NOME_PASTA / NOME_FICHEIRO)
    candidatos.append(Path.home() / NOME_PASTA / NOME_FICHEIRO)

    for caminho in candidatos:
        try:
            caminho.parent.mkdir(parents=True, exist_ok=True)
            with caminho.open("a", encoding="utf-8"):
                pass
            return caminho
        except OSError:
            continue
    return Path(NOME_FICHEIRO).resolve()


def ficheiros_do_diario() -> list[Path]:
    """Every diary file that exists (the current one plus the rotated ones)."""
    atual = caminho_diario()
    ficheiros = [atual] if atual.is_file() else []
    for indice in range(1, COPIAS + 1):
        copia = atual.with_name(f"{atual.name}.{indice}")
        if copia.is_file():
            ficheiros.append(copia)
    return ficheiros


class _ContextoFilter(logging.Filter):
    """Put who/where/which obra on every record, whoever logged it."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 (API do logging)
        for campo, valor in _CONTEXTO.items():
            setattr(record, campo, getattr(record, campo, None) or valor)
        return True


def configurar_diario(nivel: int = logging.INFO) -> Path:
    """Install the rotating file handler on the root logger (idempotent)."""
    global _handler

    caminho = caminho_diario()
    if _handler is not None:
        return caminho

    handler = RotatingFileHandler(
        caminho,
        maxBytes=MAX_BYTES,
        backupCount=COPIAS,
        encoding="utf-8",
        delay=True,
    )
    handler.setFormatter(logging.Formatter(FORMATO, datefmt=FORMATO_DATA))
    handler.addFilter(_ContextoFilter())
    handler.setLevel(nivel)

    raiz = logging.getLogger()
    raiz.addHandler(handler)
    if raiz.level > nivel:
        raiz.setLevel(nivel)
    _handler = handler
    return caminho


# ---- contexto ---------------------------------------------------------------
def definir_utilizador(nome: object) -> None:
    _CONTEXTO["utilizador"] = _limpo(nome)


def definir_menu(nome: object) -> None:
    _CONTEXTO["menu"] = _limpo(nome)


def definir_obra(codigo: object) -> None:
    _CONTEXTO["obra"] = _limpo(codigo)


def contexto_atual() -> dict[str, str]:
    """Snapshot of who/where/which obra, for the problem report."""
    return dict(_CONTEXTO)


def _limpo(valor: object) -> str:
    texto = str(valor or "").strip().replace("|", "/").replace("\n", " ")
    return texto or "-"


# ---- escrever ---------------------------------------------------------------
def registar_arranque(versao: str = "") -> None:
    """First line of a session: PC, Windows, Python and version."""
    _LOGGER.info(
        "Martelo iniciado (versao=%s, PC=%s, SO=%s, Python=%s)",
        versao or "?",
        platform.node(),
        platform.platform(),
        platform.python_version(),
    )


def registar_acao(acao: str, detalhe: object = "") -> None:
    """One line per relevant action (open menu, save, export...)."""
    texto = str(detalhe or "").strip()
    _LOGGER.info("%s%s", acao, f" — {texto}" if texto else "")


def registar_aviso(titulo: str, mensagem: object = "") -> None:
    """Something the Martelo warned the user about."""
    _LOGGER.warning("AVISO %s: %s", titulo, _uma_linha(mensagem))


def registar_erro(titulo: str, mensagem: object = "", *, erro: BaseException | None = None) -> None:
    """An error, with the traceback when there is one."""
    excecao = erro or (sys.exc_info()[1] if sys.exc_info()[0] else None)
    _LOGGER.error(
        "ERRO %s: %s",
        titulo,
        _uma_linha(mensagem),
        exc_info=excecao if excecao is not None else False,
    )


def _uma_linha(mensagem: object) -> str:
    return " ".join(str(mensagem or "").split())


# ---- erros inesperados ------------------------------------------------------
def instalar_apanhador_de_erros() -> None:
    """Send crashes that nobody caught to the diary, in the main and worker threads."""
    anterior = sys.excepthook

    def _excepthook(tipo, valor, tb):
        try:
            _LOGGER.error(
                "ERRO inesperado: %s", valor, exc_info=(tipo, valor, tb)
            )
        finally:
            anterior(tipo, valor, tb)

    sys.excepthook = _excepthook

    def _thread_excepthook(args):
        _LOGGER.error(
            "ERRO inesperado na thread %s: %s",
            getattr(args.thread, "name", "?"),
            args.exc_value,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    threading.excepthook = _thread_excepthook


# ---- ler de volta -----------------------------------------------------------
def linhas_recentes(maximo: int = 400) -> list[str]:
    """Last lines of the diary — what goes into the problem report."""
    caminho = caminho_diario()
    try:
        with caminho.open("r", encoding="utf-8", errors="replace") as ficheiro:
            linhas = ficheiro.readlines()
    except OSError:
        return []
    return [linha.rstrip("\n") for linha in linhas[-maximo:]]
