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

import faulthandler
import logging
import os
import platform
import sys
import tempfile
import threading
import time
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
_caminho_em_uso: Path | None = None


# ---- onde vive o ficheiro ---------------------------------------------------
def caminho_diario(preferido: str | Path | None = None) -> Path:
    """Return a writable local path for the diary (never on the server).

    ``preferido`` é o que estiver em Configurações → Caminhos do Sistema
    ("Ficheiro de log"): serve para quem quiser o registo noutro sítio. Um
    caminho de rede é ignorado de propósito — escrever o registo no servidor
    seria lento e o ficheiro ficaria preso a cada arranque.
    """
    if preferido is None and _caminho_em_uso is not None:
        return _caminho_em_uso

    candidatos: list[Path] = []
    escolhido = str(preferido or "").strip()
    if escolhido and not _e_caminho_de_rede(escolhido):
        candidatos.append(Path(escolhido).expanduser())

    explicito = (os.getenv("MARTELO_DIARIO_PATH") or "").strip()
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


def _e_caminho_de_rede(caminho: str) -> bool:
    return caminho.startswith("\\\\") or caminho.startswith("//")


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


def configurar_diario(
    nivel: int = logging.INFO, *, preferido: str | Path | None = None
) -> Path:
    """Install the rotating file handler on the root logger (idempotent)."""
    global _handler, _caminho_em_uso

    if _handler is not None:
        return caminho_diario()

    caminho = caminho_diario(preferido)
    _caminho_em_uso = caminho

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

    escolhido = str(preferido or "").strip()
    if escolhido and caminho != Path(escolhido).expanduser():
        # Fica escrito no próprio diário: assim, quem configurou o caminho
        # percebe porque é que o ficheiro não apareceu lá.
        _LOGGER.warning(
            "O 'Ficheiro de log' configurado (%s) não foi usado — o registo é "
            "sempre local: %s",
            escolhido,
            caminho,
        )
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


# ---- crashes que matam o processo -------------------------------------------
#: Quando o Qt ou o Python rebentam "por baixo" (violação de acesso), o processo
#: morre de uma vez: não há excepção, o excepthook não corre e o diário fica
#: sem nada. O ``faulthandler`` do Python escreve NESSE instante, direto no
#: ficheiro, em que linha do código estava cada thread. Foi o que faltou a
#: 18-09-2026, quando o Martelo se fechou sozinho três vezes no 260932_01.
NOME_CRASH = "crash_martelo.log"
PADRAO_CRASH_GUARDADO = "crash_martelo_*.log"
MARCA_SAIDA_NORMAL = "=== saída normal ==="
_MARCAS_CRASH = ("Windows fatal exception", "Fatal Python error")

_ficheiro_crash = None


def caminho_crash() -> Path:
    return (_caminho_em_uso or caminho_diario()).with_name(NOME_CRASH)


def resumo_crash(texto: str, *, maximo_linhas: int = 120) -> str | None:
    """O relatório do faulthandler, se a sessão acabou num crash; senão None.

    Uma sessão que chegou ao fim marca-se com :data:`MARCA_SAIDA_NORMAL`; se a
    marca lá está, qualquer aviso interno que tenha ficado escrito não conta.
    """
    if not texto or MARCA_SAIDA_NORMAL in texto:
        return None
    linhas = texto.splitlines()
    inicio = next(
        (i for i, linha in enumerate(linhas) if linha.startswith(_MARCAS_CRASH)),
        None,
    )
    if inicio is None:
        return None
    return "\n".join(linhas[inicio : inicio + maximo_linhas]).strip()


def instalar_registo_de_crash() -> str | None:
    """Ligar o faulthandler e trazer para o diário o crash da sessão anterior.

    Devolve o relatório desse crash (ou None) -- para quem quiser avisar.
    """
    global _ficheiro_crash
    caminho = caminho_crash()
    anterior = None
    try:
        anterior = resumo_crash(caminho.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        anterior = None
    if anterior:
        _LOGGER.error(
            "O Martelo fechou-se sozinho na sessão anterior (crash sem mensagem). "
            "Onde estava cada parte do programa:\n%s",
            anterior,
        )
        try:
            guardado = caminho.with_name(
                f"crash_martelo_{time.strftime('%Y%m%d_%H%M%S')}.log"
            )
            caminho.replace(guardado)
        except OSError:
            pass

    try:
        ficheiro = open(caminho, "w", encoding="utf-8")  # noqa: SIM115 - fica aberto de propósito
        ficheiro.write(
            f"=== arranque {time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"(PID {os.getpid()}) ===\n"
        )
        ficheiro.flush()
        faulthandler.enable(file=ficheiro, all_threads=True)
        _ficheiro_crash = ficheiro
    except (OSError, RuntimeError, ValueError):
        _LOGGER.warning("Não foi possível ligar o registo de crashes em %s", caminho)
    return anterior


def marcar_saida_normal() -> None:
    """A sessão acabou bem: o próximo arranque não a conta como crash."""
    if _ficheiro_crash is None:
        return
    try:
        _ficheiro_crash.write(f"{MARCA_SAIDA_NORMAL}\n")
        _ficheiro_crash.flush()
    except (OSError, ValueError):
        pass


# ---- limpeza automática -----------------------------------------------------
#: Guardamos um mês de história: chega para investigar e não deixa lixo no PC.
DIAS_A_GUARDAR = 30

#: Relatórios de problema que ficam na pasta temporária ao enviar por email.
PADRAO_RELATORIOS = "problema_martelo_*.txt"


def limpar_registos_antigos(
    dias: int = DIAS_A_GUARDAR, *, agora: float | None = None
) -> list[Path]:
    """Delete diary copies and problem reports older than ``dias``.

    Corre sozinho no arranque do Martelo, para o registo não ir engordando o PC
    sem ninguém dar por isso. Mexe **apenas** em ficheiros criados por nós: as
    cópias rodadas do diário e os relatórios que ficaram na pasta temporária.
    O ficheiro em uso nunca é apagado — é o que tem o que se passou hoje.
    """
    limite = (agora if agora is not None else time.time()) - dias * 86400
    apagados: list[Path] = []

    atual = caminho_diario()
    candidatos = [
        atual.with_name(f"{atual.name}.{indice}") for indice in range(1, COPIAS + 1)
    ]
    try:
        candidatos.extend(Path(tempfile.gettempdir()).glob(PADRAO_RELATORIOS))
    except OSError:
        pass
    try:
        candidatos.extend(atual.parent.glob(PADRAO_CRASH_GUARDADO))
    except OSError:
        pass

    for ficheiro in candidatos:
        try:
            if not ficheiro.is_file() or ficheiro.stat().st_mtime >= limite:
                continue
            ficheiro.unlink()
            apagados.append(ficheiro)
        except OSError:
            # Ficheiro aberto noutro lado ou sem permissões: fica para a próxima.
            continue

    if apagados:
        _LOGGER.info(
            "Limpeza automática: %s ficheiro(s) de registo com mais de %s dias apagados.",
            len(apagados),
            dias,
        )
    return apagados


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
