"""Captura as janelas do Martelo para os guias, sem o que estiver por cima.

Usa o PrintWindow do Windows janela a janela (principal, diálogos, menus abertos)
e junta-as pela ordem em que estão no ecrã, recortadas ao monitor onde está a
janela principal. Assim o print sai limpo mesmo com outra janela à frente.

Uso:
    python capturar_janela.py <saida.png>            # o ecrã do Martelo inteiro
    python capturar_janela.py <saida.png> --so-topo  # só o diálogo de cima
    python capturar_janela.py <saida.png> --pid 1234 # outro processo

Sem --pid procura a janela cujo título começa por «Martelo Orçamentos V3».
"""

from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes

ctypes.windll.shcore.SetProcessDpiAwareness(2)

from PIL import Image  # noqa: E402

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
dwmapi = ctypes.windll.dwmapi

PW_RENDERFULLCONTENT = 2
DWMWA_EXTENDED_FRAME_BOUNDS = 9
MONITOR_DEFAULTTONEAREST = 2
TITULO_MARTELO = "Martelo Orçamentos V3"


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def _titulo(hwnd) -> str:
    tamanho = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(tamanho + 1)
    user32.GetWindowTextW(hwnd, buf, tamanho + 1)
    return buf.value


def _pid(hwnd) -> int:
    p = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(p))
    return p.value


def _janelas_visiveis():
    """Todas as janelas visíveis, a de cima primeiro (ordem do EnumWindows)."""
    lista = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _l):
        if user32.IsWindowVisible(hwnd):
            r = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(r))
            if r.right - r.left > 4 and r.bottom - r.top > 4:
                lista.append(hwnd)
        return True

    user32.EnumWindows(cb, 0)
    return lista


def _rect(hwnd):
    r = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return r.left, r.top, r.right, r.bottom


def _rect_visivel(hwnd):
    """O retângulo sem a sombra invisível que o Windows põe à volta."""
    r = wintypes.RECT()
    if dwmapi.DwmGetWindowAttribute(
        hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(r), ctypes.sizeof(r)
    ) == 0:
        return r.left, r.top, r.right, r.bottom
    return _rect(hwnd)


def _monitor_de(hwnd):
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(info)
    user32.GetMonitorInfoW(
        user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST), ctypes.byref(info)
    )
    r = info.rcWork  # sem a barra de tarefas
    return r.left, r.top, r.right, r.bottom


def _imprimir(hwnd):
    l, t, r, b = _rect(hwnd)
    w, h = r - l, b - t
    hdc_win = user32.GetWindowDC(hwnd)
    hdc = gdi32.CreateCompatibleDC(hdc_win)
    bmp = gdi32.CreateCompatibleBitmap(hdc_win, w, h)
    gdi32.SelectObject(hdc, bmp)
    user32.PrintWindow(hwnd, hdc, PW_RENDERFULLCONTENT)
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(bi)
    bi.biWidth, bi.biHeight, bi.biPlanes, bi.biBitCount = w, -h, 1, 32
    buf = ctypes.create_string_buffer(w * h * 4)
    gdi32.GetDIBits(hdc, bmp, 0, h, buf, ctypes.byref(bi), 0)
    gdi32.DeleteObject(bmp)
    gdi32.DeleteDC(hdc)
    user32.ReleaseDC(hwnd, hdc_win)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    vl, vt, vr, vb = _rect_visivel(hwnd)
    return img.crop((vl - l, vt - t, vr - l, vb - t)), (vl, vt, vr, vb)


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    saida = sys.argv[1]
    so_topo = "--so-topo" in sys.argv
    todas = _janelas_visiveis()

    if "--pid" in sys.argv:
        pid = int(sys.argv[sys.argv.index("--pid") + 1])
    else:
        principal = next((h for h in todas if _titulo(h).startswith(TITULO_MARTELO)), None)
        if principal is None:
            raise SystemExit(f"Não encontrei nenhuma janela «{TITULO_MARTELO}…» aberta.")
        pid = _pid(principal)

    janelas = [h for h in todas if _pid(h) == pid]
    if not janelas:
        raise SystemExit(f"O processo {pid} não tem janelas visíveis.")

    if so_topo:
        img, _ = _imprimir(janelas[0])
        img.save(saida)
        print(saida, img.size)
        return

    principal = next(
        (h for h in janelas if _titulo(h).startswith(TITULO_MARTELO)), janelas[-1]
    )
    ml, mt, mr, mb = _monitor_de(principal)
    tela = Image.new("RGB", (mr - ml, mb - mt), (240, 240, 240))
    for hwnd in reversed(janelas):  # de baixo para cima
        img, (l, t, _r, _b) = _imprimir(hwnd)
        tela.paste(img, (l - ml, t - mt))
    tela.save(saida)
    print(saida, tela.size, len(janelas), "janela(s)")


if __name__ == "__main__":
    main()
