"""Carregar os runtimes C++ comuns antes das cópias privadas de Qt/sklearn.

No perfil completo, as bibliotecas trazem versões diferentes destas DLLs.
Carregar primeiro a versão comum recolhida pelo PyInstaller evita que o
shiboken fixe uma cópia antiga e o QtCore falhe com um símbolo em falta.
"""
import ctypes
import os
import sys

if sys.platform == 'win32' and getattr(sys, 'frozen', False):
    for name in ('vcruntime140.dll', 'vcruntime140_1.dll', 'msvcp140.dll'):
        path = os.path.join(sys._MEIPASS, name)
        if os.path.isfile(path):
            ctypes.WinDLL(path)
