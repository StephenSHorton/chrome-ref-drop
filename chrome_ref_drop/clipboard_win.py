"""Windows clipboard helpers for image paste (PNG / DIB)."""

from __future__ import annotations

import ctypes
import struct
from ctypes import wintypes
from typing import Optional, Tuple

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CF_UNICODETEXT = 13
CF_DIB = 8
CF_HDROP = 15

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE
user32.RegisterClipboardFormatW.argtypes = [wintypes.LPCWSTR]
user32.RegisterClipboardFormatW.restype = wintypes.UINT

kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalSize.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalSize.restype = ctypes.c_size_t


def _cf_png() -> int:
    return user32.RegisterClipboardFormatW("PNG")


def get_clipboard_text() -> Optional[str]:
    if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            text = ctypes.wstring_at(ptr)
            return text
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def get_clipboard_png_bytes() -> Optional[bytes]:
    fmt = _cf_png()
    if not user32.IsClipboardFormatAvailable(fmt):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(fmt)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            size = kernel32.GlobalSize(handle)
            if not size:
                return None
            return ctypes.string_at(ptr, size)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def _dib_to_bmp_bytes(dib: bytes) -> bytes:
    """Wrap a CF_DIB payload (BITMAPINFOHEADER + pixels) as a .bmp file."""
    if len(dib) < 40:
        raise ValueError("DIB too small")
    header_size = struct.unpack_from("<I", dib, 0)[0]
    if header_size < 40:
        raise ValueError("Invalid BITMAPINFOHEADER")

    # BITMAPFILEHEADER is 14 bytes
    file_size = 14 + len(dib)
    pixel_offset = 14 + header_size

    # Color table for <= 8bpp
    bit_count = struct.unpack_from("<H", dib, 14)[0] if header_size >= 16 else 0
    # biBitCount is at offset 14 within BITMAPINFOHEADER
    bit_count = struct.unpack_from("<H", dib, 14)[0]
    clr_used = struct.unpack_from("<I", dib, 32)[0]
    if bit_count <= 8:
        n_colors = clr_used if clr_used else (1 << bit_count)
        pixel_offset = 14 + header_size + n_colors * 4

    bmp_header = struct.pack("<HIII", 0x4D42, file_size, 0, pixel_offset)
    return bmp_header + dib


def get_clipboard_dib_as_bmp() -> Optional[bytes]:
    if not user32.IsClipboardFormatAvailable(CF_DIB):
        return None
    if not user32.OpenClipboard(None):
        return None
    try:
        handle = user32.GetClipboardData(CF_DIB)
        if not handle:
            return None
        ptr = kernel32.GlobalLock(handle)
        if not ptr:
            return None
        try:
            size = kernel32.GlobalSize(handle)
            if not size:
                return None
            dib = ctypes.string_at(ptr, size)
            return _dib_to_bmp_bytes(dib)
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def get_clipboard_image_bytes() -> Optional[Tuple[bytes, str]]:
    """
    Return (bytes, extension) for an image on the clipboard, if any.
    Prefers PNG (lossless from Chrome 'Copy image'), then DIB→BMP.
    """
    png = get_clipboard_png_bytes()
    if png:
        return png, ".png"
    bmp = get_clipboard_dib_as_bmp()
    if bmp:
        return bmp, ".bmp"
    return None
