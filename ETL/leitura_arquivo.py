"""Leitura sem escrita, inclusive quando o Excel permite acesso compartilhado."""
import os
from pathlib import Path


def ler_bytes(caminho):
    try:
        return Path(caminho).read_bytes()
    except PermissionError:
        if os.name != "nt":
            raise
        import ctypes
        import msvcrt
        api = ctypes.windll.kernel32.CreateFileW
        api.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                       ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        api.restype = ctypes.c_void_p
        handle = api(str(caminho), 0x80000000, 7, None, 3, 0, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError()
        with os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY), "rb") as stream:
            return stream.read()
