"""Abrir uma obra no iX CAD a partir do Martelo, como o «Abrir iX CAD» do Organizer.

Como o Organizer faz (lido no próprio programa da imos AG, iguais no iX 2023 e
no 2025): o iX CAD, quando está aberto, deixa à escuta um canal de memória
partilhada (`IMOS_MMF_IPC_SERVER`, com o evento `IMOS_MMF_IPC_SERVER_LOCK`). O
Organizer escreve lá, em UTF-16, ``<IMOS_COMMAND>imosopendwg "<Imorder>\\<obra>\\<obra>.dwg"``,
liga o evento durante 600 ms e desliga-o. O ``imosopendwg`` é um comando do
próprio iMos: abre a obra com as propriedades do iMos, não é só abrir o .dwg.
Com o iX CAD fechado, o Organizer arranca-o (``imos.exe /nologo``) e espera que
o canal apareça antes de pedir a obra.

A automação COM do AutoCAD não serve: o iX CAD é um AutoCAD OEM com essa porta
fechada (responde, mas devolve erro a tudo).

O Martelo não escreve nada na base do iMos — só lê, para confirmar que a
encomenda existe. Quem abre e grava o desenho é o próprio iX CAD.
"""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from app.services import imos_sql
from app.services.imos_sql import (
    IMOS_TIPO_ENCOMENDA_EM_PRODUCAO,
    IMOS_TIPO_ENCOMENDA_REFERENCIA,
    ImosConfig,
    NoImos,
)

TITULO = "Abrir no iX CAD"

# Canal do iX CAD (`imosLibrary.dll` › MMF_IPC_Client; servidor no imosr25.arx).
CANAL = "IMOS_MMF_IPC_SERVER"
EVENTO_CANAL = CANAL + "_LOCK"
TAMANHO_CANAL = 512_000
PAUSA_EVENTO_S = 0.6

# Arranque como o Organizer: ACADPATH + ACADPARAM, na pasta BIN da instalação.
PARAMETROS_ARRANQUE = ("/nologo",)
# O Organizer espera 1,5 s depois de o canal aparecer e mais 0,5 s antes de
# pedir a obra; o iX CAD acabado de arrancar ainda está a carregar o iMos.
ESPERA_DEPOIS_DO_CANAL_S = 3.0
ESPERA_ARRANQUE_S = 180

CHAVE_REGISTO_IMOS = r"SOFTWARE\imos AG\IMOSACT"
DEFAULT_PASTA_IMORDER = r"I:\Factory\Imorder"

ESTADO_CANAL_ATIVO = "ativo"
ESTADO_CANAL_FECHADO = "fechado"
ESTADO_CANAL_SEM_ACESSO = "sem_acesso"

MENSAGEM_ELEVADO = (
    "O Martelo está a correr como administrador e, assim, não consegue falar "
    "com o iX CAD — e se o abrisse, o iX CAD ficava com a conta de "
    "administrador, sem a unidade I: dos desenhos.\n\n"
    "Feche o Martelo e volte a abri-lo pelo atalho normal. Se voltar a "
    "acontecer, veja no atalho: Propriedades > Compatibilidade > «Executar "
    "este programa como administrador» tem de estar desmarcado."
)


class ErroIxCad(RuntimeError):
    """Algo impede abrir a obra; a mensagem já está pronta para o utilizador."""


# --------------------------------------------------------------------------
# Instalação do iX CAD neste PC
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class InstalacaoIxCad:
    versao: int
    executavel: Path
    pasta_trabalho: Path
    pasta_imorder: str


def _versao_da_chave(nome: str) -> int | None:
    digitos = nome.split(".", 1)[0]
    return int(digitos) if digitos.isdigit() else None


def _ler_instalacoes_registo() -> list[tuple[int, dict[str, str]]]:
    """Cada versão do iMos instalada: `IMOSACT\\<versão>\\Install` (16 = 2023, 17 = 2025)."""
    if sys.platform != "win32":
        return []
    import winreg

    instalacoes: list[tuple[int, dict[str, str]]] = []
    acesso = winreg.KEY_READ | winreg.KEY_WOW64_64KEY
    try:
        raiz = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, CHAVE_REGISTO_IMOS, 0, acesso)
    except OSError:
        return instalacoes
    with raiz:
        indice = 0
        while True:
            try:
                subchave = winreg.EnumKey(raiz, indice)
            except OSError:
                break
            indice += 1
            versao = _versao_da_chave(subchave)
            if versao is None:
                continue
            try:
                with winreg.OpenKey(raiz, subchave + r"\Install", 0, acesso) as chave:
                    valores: dict[str, str] = {}
                    posicao = 0
                    while True:
                        try:
                            nome, valor, _tipo = winreg.EnumValue(chave, posicao)
                        except OSError:
                            break
                        posicao += 1
                        if isinstance(valor, str):
                            valores[nome.upper()] = valor.strip()
            except OSError:
                continue
            instalacoes.append((versao, valores))
    return instalacoes


def localizar_instalacao(
    *,
    ler: Callable[[], list[tuple[int, dict[str, str]]]] = _ler_instalacoes_registo,
    existe: Callable[[str], bool] = os.path.isfile,
) -> InstalacaoIxCad | None:
    """A versão mais recente do iX CAD instalada neste PC, ou ``None``."""
    for versao, valores in sorted(ler(), key=lambda par: par[0], reverse=True):
        executavel = valores.get("ACADPATH", "")
        if not executavel or not existe(executavel):
            continue
        pasta_imos = valores.get("IMOS") or str(Path(executavel).parent.parent)
        return InstalacaoIxCad(
            versao=versao,
            executavel=Path(executavel),
            pasta_trabalho=Path(pasta_imos) / "BIN",
            pasta_imorder=valores.get("IMORDERPATH", ""),
        )
    return None


def pasta_imorder_a_usar(
    instalacao: InstalacaoIxCad | None, valor_martelo: str | None
) -> str:
    """A pasta dos desenhos: a do iX CAD deste PC vale primeiro (é a que ele usa)."""
    if instalacao is not None and instalacao.pasta_imorder:
        return instalacao.pasta_imorder
    return (valor_martelo or "").strip() or DEFAULT_PASTA_IMORDER


# --------------------------------------------------------------------------
# Peças do pedido (sem Windows)
# --------------------------------------------------------------------------


def caminho_desenho(pasta_imorder: str, nome_encomenda: str) -> Path:
    """A pasta do iMos é plana: `<Imorder>\\<obra>\\<obra>.dwg`, seja qual for a árvore."""
    return Path(pasta_imorder) / nome_encomenda / f"{nome_encomenda}.dwg"


def comando_abrir(desenho: Path | str) -> str:
    return f'imosopendwg "{desenho}"'


def mensagem_canal(comando: str) -> bytes:
    """O texto que o Organizer escreve no canal (`<{0}>{1}`, UTF-16)."""
    dados = f"<IMOS_COMMAND>{comando}".encode("utf-16-le") + b"\0\0"
    if len(dados) > TAMANHO_CANAL:
        raise ErroIxCad("O pedido para o iX CAD é demasiado comprido.")
    return dados


@dataclass(frozen=True)
class TrancaDesenho:
    """O `.dwl` que o iX CAD escreve ao lado do desenho enquanto o tem aberto."""

    utilizador: str
    computador: str
    desde: str


def ler_tranca(desenho: Path) -> TrancaDesenho | None:
    """Quem tem a obra aberta, segundo o `.dwl`; ``None`` se não houver."""
    try:
        bruto = desenho.with_suffix(".dwl").read_bytes()
    except OSError:
        return None
    codificacao = "mbcs" if sys.platform == "win32" else "cp1252"
    linhas = [linha.strip() for linha in bruto.decode(codificacao, "replace").splitlines()]
    if len(linhas) < 2 or not linhas[0]:
        return None
    return TrancaDesenho(
        utilizador=linhas[0],
        computador=linhas[1],
        desde=linhas[2] if len(linhas) > 2 else "",
    )


@dataclass(frozen=True)
class PlanoAbertura:
    encomenda: NoImos
    desenho: Path
    desenho_existe: bool
    ja_aberta_neste_pc: bool
    tranca_de_outro_posto: TrancaDesenho | None = None

    @property
    def nome(self) -> str:
        return self.encomenda.nome

    @property
    def comando(self) -> str:
        return comando_abrir(self.desenho)

    def avisos(self) -> list[str]:
        """O que o utilizador tem de saber antes de abrir (os do Organizer e mais)."""
        avisos: list[str] = []
        if self.encomenda.tipo == IMOS_TIPO_ENCOMENDA_REFERENCIA:
            avisos.append(
                "É uma encomenda de referência: as alterações afetam todas as "
                "referências."
            )
        if self.encomenda.tipo == IMOS_TIPO_ENCOMENDA_EM_PRODUCAO:
            avisos.append(
                "A encomenda está em produção e bloqueada para alterações."
            )
        tranca = self.tranca_de_outro_posto
        if tranca is not None:
            desde = f" (desde {tranca.desde})" if tranca.desde else ""
            avisos.append(
                f"Está aberta por {tranca.utilizador} no PC {tranca.computador}"
                f"{desde}. O iX CAD deve abri-la só para leitura."
            )
        if not self.desenho_existe:
            avisos.append(
                "A obra ainda não tem desenho: o iX CAD vai criar um desenho novo "
                "para esta encomenda."
            )
        return avisos


def preparar_abertura(
    cfg: ImosConfig,
    nome: str,
    *,
    dir_id: int | None,
    pasta_imorder: str,
    procurar: Callable[..., NoImos | None] | None = None,
    abertos: Callable[[], frozenset[str]] | None = None,
    computador: str | None = None,
) -> PlanoAbertura:
    """Confirma tudo o que se pode confirmar antes de mexer no iX CAD.

    Uma encomenda que não exista no iMos nunca chega ao iX CAD: nem todas
    as obras têm encomenda criada, e nem todas foram criadas pelo Martelo.
    """
    nome = (nome or "").strip()
    if not nome and not dir_id:
        raise ErroIxCad(
            "A obra não tem «Nome Enc IMOS IX»: é por ele que o Martelo encontra "
            "a encomenda no iMos."
        )
    if not (cfg.get("server") and cfg.get("database")):
        raise ErroIxCad(
            "A ligação ao iMos não está configurada, por isso não consigo "
            "confirmar que a encomenda existe.\n\nConfigurações > Ligação iMos."
        )

    encomenda = (procurar or imos_sql.procurar_encomenda_para_abrir)(
        cfg, nome, dir_id=dir_id
    )
    if encomenda is None:
        raise ErroIxCad(
            f"A encomenda «{nome}» não existe no iX Organizer, por isso não pode "
            "ser aberta no iX CAD.\n\nCrie-a primeiro: Funções > Criar Encomenda "
            "IMOS… ou no próprio Organizer."
        )

    desenho = caminho_desenho(pasta_imorder, encomenda.nome)
    if not desenho.parent.is_dir():
        raise ErroIxCad(
            "A encomenda existe no iMos, mas a pasta dela não foi encontrada:\n"
            f"{desenho.parent}\n\nConfirme se a unidade dos desenhos do iMos "
            "(I:) está ligada neste PC."
        )

    ja_aberta = f"{encomenda.nome}.DWG".upper() in (abertos or desenhos_abertos)()
    existe = desenho.is_file()
    tranca = None
    if existe and not ja_aberta:
        lida = ler_tranca(desenho)
        este_pc = (computador or os.environ.get("COMPUTERNAME", "")).strip()
        # Um `.dwl` deste PC sem a obra aberta é resto de um iX CAD que fechou
        # mal: o próprio iX CAD trata disso ao abrir.
        if lida is not None and lida.computador.casefold() != este_pc.casefold():
            tranca = lida

    return PlanoAbertura(
        encomenda=encomenda,
        desenho=desenho,
        desenho_existe=existe,
        ja_aberta_neste_pc=ja_aberta,
        tranca_de_outro_posto=tranca,
    )


# --------------------------------------------------------------------------
# Windows: o canal, as janelas do iX CAD e o arranque
# --------------------------------------------------------------------------

_SYNCHRONIZE = 0x00100000
_EVENT_MODIFY_STATE = 0x0002
_FILE_MAP_WRITE = 0x0002
_FILE_MAP_READ = 0x0004
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_ERROR_ACCESS_DENIED = 5
_TOKEN_QUERY = 0x0008
_TOKEN_ELEVATION_TYPE = 18
_TOKEN_ELEVATION_TYPE_FULL = 2
_SW_RESTORE = 9

_k32 = None
_u32 = None


def _kernel32():
    global _k32
    if _k32 is None:
        from ctypes import wintypes

        k = ctypes.WinDLL("kernel32", use_last_error=True)
        k.OpenEventW.restype = wintypes.HANDLE
        k.OpenEventW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        k.SetEvent.argtypes = [wintypes.HANDLE]
        k.ResetEvent.argtypes = [wintypes.HANDLE]
        k.OpenFileMappingW.restype = wintypes.HANDLE
        k.OpenFileMappingW.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
        k.MapViewOfFile.restype = ctypes.c_void_p
        k.MapViewOfFile.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_size_t,
        ]
        k.UnmapViewOfFile.argtypes = [ctypes.c_void_p]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.OpenProcess.restype = wintypes.HANDLE
        k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        k.GetCurrentProcess.restype = wintypes.HANDLE
        _k32 = k
    return _k32


def _user32():
    global _u32
    if _u32 is None:
        from ctypes import wintypes

        u = ctypes.WinDLL("user32", use_last_error=True)
        u.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        u.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        u.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        u.IsWindowVisible.argtypes = [wintypes.HWND]
        u.IsIconic.argtypes = [wintypes.HWND]
        u.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        u.SetForegroundWindow.argtypes = [wintypes.HWND]
        _u32 = u
    return _u32


def estado_canal() -> str:
    """Se o iX CAD está aberto e pronto a receber pedidos."""
    if sys.platform != "win32":
        return ESTADO_CANAL_FECHADO
    k = _kernel32()
    evento = k.OpenEventW(_SYNCHRONIZE, False, EVENTO_CANAL)
    if not evento:
        # Aberto por outra conta (o Martelo elevado como administrador) vê-se
        # como acesso negado; fechado é "não existe".
        if ctypes.get_last_error() == _ERROR_ACCESS_DENIED:
            return ESTADO_CANAL_SEM_ACESSO
        return ESTADO_CANAL_FECHADO
    k.CloseHandle(evento)
    return ESTADO_CANAL_ATIVO


def enviar_comando(comando: str) -> None:
    """Escreve o pedido no canal e acorda o iX CAD, como o Organizer."""
    dados = mensagem_canal(comando)
    if sys.platform != "win32":
        raise ErroIxCad("O iX CAD só existe no Windows.")
    k = _kernel32()
    evento = k.OpenEventW(_SYNCHRONIZE | _EVENT_MODIFY_STATE, False, EVENTO_CANAL)
    if not evento:
        raise ErroIxCad("O iX CAD não está aberto (ou ainda não está pronto).")
    try:
        mapa = k.OpenFileMappingW(_FILE_MAP_READ | _FILE_MAP_WRITE, False, CANAL)
        if not mapa:
            raise ErroIxCad(
                "O iX CAD está aberto, mas o canal de comunicação não respondeu."
            )
        try:
            vista = k.MapViewOfFile(mapa, _FILE_MAP_READ | _FILE_MAP_WRITE, 0, 0, TAMANHO_CANAL)
            if not vista:
                raise ErroIxCad(
                    "O iX CAD está aberto, mas o canal de comunicação não respondeu."
                )
            try:
                # O iX CAD apaga o canal depois de ler; se ainda tem texto, o
                # pedido anterior não foi lido e não se escreve por cima.
                if ctypes.string_at(vista, 16) != b"\0" * 16:
                    raise ErroIxCad(
                        "O iX CAD ainda não leu o pedido anterior. Espere um "
                        "pouco e tente outra vez."
                    )
                ctypes.memmove(vista, dados, len(dados))
            finally:
                k.UnmapViewOfFile(vista)
        finally:
            k.CloseHandle(mapa)
        k.SetEvent(evento)
        time.sleep(PAUSA_EVENTO_S)
        k.ResetEvent(evento)
    finally:
        k.CloseHandle(evento)


def _nome_executavel(pid: int) -> str:
    from ctypes import wintypes

    k = _kernel32()
    processo = k.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not processo:
        return ""
    try:
        tamanho = wintypes.DWORD(1024)
        texto = ctypes.create_unicode_buffer(tamanho.value)
        if not k.QueryFullProcessImageNameW(processo, 0, texto, ctypes.byref(tamanho)):
            return ""
        return Path(texto.value).name
    finally:
        k.CloseHandle(processo)


def _texto_janela(hwnd) -> str:
    u = _user32()
    tamanho = u.GetWindowTextLengthW(hwnd)
    if tamanho <= 0:
        return ""
    texto = ctypes.create_unicode_buffer(tamanho + 1)
    u.GetWindowTextW(hwnd, texto, tamanho + 1)
    return texto.value


def _janelas_ix_cad() -> list[tuple[int, str]]:
    """(janela, título) das janelas principais dos processos `imos.exe`."""
    if sys.platform != "win32":
        return []
    from ctypes import wintypes

    u = _user32()
    executaveis: dict[int, str] = {}
    janelas: list[tuple[int, str]] = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cada(hwnd, _lparam):
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value not in executaveis:
            executaveis[pid.value] = _nome_executavel(pid.value).casefold()
        if executaveis[pid.value] == "imos.exe":
            janelas.append((hwnd, _texto_janela(hwnd)))
        return True

    u.EnumWindows(_cada, 0)
    return janelas


def desenhos_abertos() -> frozenset[str]:
    """Os desenhos abertos no iX CAD deste PC, em maiúsculas (ex.: `1702_01_26_JF_VIVA.DWG`).

    Lê-se pelo título das janelas dos separadores: é o que o Windows mostra e
    não depende da automação que o iX CAD tem fechada.
    """
    if sys.platform != "win32":
        return frozenset()
    from ctypes import wintypes

    u = _user32()
    nomes: set[str] = set()

    def _juntar(titulo: str) -> None:
        # A «iX CAD Text Window - <obra>.dwg» também acaba em .dwg; não é um separador.
        if titulo.casefold().endswith(".dwg") and not titulo.casefold().startswith("ix cad"):
            nomes.add(titulo.upper())

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _filho(hwnd, _lparam):
        _juntar(_texto_janela(hwnd))
        return True

    for hwnd, titulo in _janelas_ix_cad():
        _juntar(titulo)
        u.EnumChildWindows(hwnd, _filho, 0)
    return frozenset(nomes)


def trazer_para_frente() -> bool:
    """Passa a janela principal do iX CAD para a frente (e restaura-a se minimizada)."""
    u = _user32() if sys.platform == "win32" else None
    for hwnd, titulo in _janelas_ix_cad():
        if not titulo.startswith("iX CAD") or titulo.startswith("iX CAD Text Window"):
            continue
        if not u.IsWindowVisible(hwnd):
            continue
        if u.IsIconic(hwnd):
            u.ShowWindow(hwnd, _SW_RESTORE)
        return bool(u.SetForegroundWindow(hwnd))
    return False


def martelo_elevado() -> bool:
    """Se o Martelo foi elevado pelo UAC (como administrador, só desta vez ou sempre).

    Com o UAC desligado tudo corre assim, o iX CAD incluído, e aí não é
    problema — por isso conta só o «elevado completo», não o ser administrador.
    """
    if sys.platform != "win32":
        return False
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    advapi.OpenProcessToken.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.HANDLE),
    ]
    advapi.GetTokenInformation.argtypes = [
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
    ]
    k = _kernel32()
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(k.GetCurrentProcess(), _TOKEN_QUERY, ctypes.byref(token)):
        return False
    try:
        tipo = wintypes.DWORD()
        devolvido = wintypes.DWORD()
        if not advapi.GetTokenInformation(
            token,
            _TOKEN_ELEVATION_TYPE,
            ctypes.byref(tipo),
            ctypes.sizeof(tipo),
            ctypes.byref(devolvido),
        ):
            return False
        return tipo.value == _TOKEN_ELEVATION_TYPE_FULL
    finally:
        k.CloseHandle(token)


def arrancar_ix_cad(instalacao: InstalacaoIxCad) -> None:
    """Abre o iX CAD como o Organizer: `imos.exe /nologo`, na pasta BIN."""
    pasta = instalacao.pasta_trabalho if instalacao.pasta_trabalho.is_dir() else None
    try:
        subprocess.Popen(
            [str(instalacao.executavel), *PARAMETROS_ARRANQUE],
            cwd=str(pasta) if pasta else None,
            close_fds=True,
        )
    except OSError as error:
        raise ErroIxCad(f"Não foi possível abrir o iX CAD:\n{error}") from error
