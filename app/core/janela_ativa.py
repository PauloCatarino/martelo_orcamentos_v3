"""O que está em primeiro plano no Windows, e há quanto tempo ninguém mexe.

Só se lê o nome do programa, o título da janela e os segundos desde a última
tecla ou movimento do rato. Nada do que se escreve, nada do ecrã.
"""

from __future__ import annotations

import ctypes
import os
import sys
from ctypes import wintypes
from typing import NamedTuple


class JanelaAtiva(NamedTuple):
    #: Executável (``imos.exe``); vazio quando o Windows não o deixa ler.
    processo: str
    titulo: str
    segundos_parado: float


_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


_api = None


def _windows():
    """Instâncias próprias das DLL: os ``argtypes`` daqui não mexem nas de outros."""
    global _api
    if _api is None:
        user32 = ctypes.WinDLL("user32")
        kernel32 = ctypes.WinDLL("kernel32")
        user32.GetForegroundWindow.restype = wintypes.HWND
        user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        user32.GetWindowThreadProcessId.argtypes = [
            wintypes.HWND,
            ctypes.POINTER(wintypes.DWORD),
        ]
        user32.GetLastInputInfo.argtypes = [ctypes.POINTER(_LASTINPUTINFO)]
        kernel32.GetTickCount.restype = wintypes.DWORD
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel32.QueryFullProcessImageNameW.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
            wintypes.LPWSTR,
            ctypes.POINTER(wintypes.DWORD),
        ]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        _api = (user32, kernel32)
    return _api


def ler_janela_ativa() -> JanelaAtiva | None:
    """A janela da frente agora, ou ``None`` se não houver ou não der para ler."""
    if sys.platform != "win32":
        return None
    try:
        user32, _kernel32 = _windows()
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        comprimento = user32.GetWindowTextLengthW(hwnd)
        texto = ctypes.create_unicode_buffer(max(comprimento, 0) + 1)
        user32.GetWindowTextW(hwnd, texto, len(texto))
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return JanelaAtiva(_nome_processo(pid.value), texto.value, segundos_parado())
    except Exception:  # noqa: BLE001 - medir tempo nunca pode partir o Martelo
        return None


def segundos_parado() -> float:
    """Segundos desde a última tecla ou movimento do rato, em qualquer programa."""
    user32, kernel32 = _windows()
    info = _LASTINPUTINFO()
    info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    # Os dois contadores dão a volta aos 49,7 dias: a diferença em 32 bits não.
    return ((kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF) / 1000.0


def _nome_processo(pid: int) -> str:
    if not pid:
        return ""
    _user32, kernel32 = _windows()
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        tamanho = wintypes.DWORD(1024)
        caminho = ctypes.create_unicode_buffer(tamanho.value)
        if not kernel32.QueryFullProcessImageNameW(
            handle, 0, caminho, ctypes.byref(tamanho)
        ):
            return ""
        return os.path.basename(caminho.value).lower()
    finally:
        kernel32.CloseHandle(handle)
