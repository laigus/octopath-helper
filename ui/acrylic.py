"""Windows Acrylic + DWM rounded corners and shadow."""

from __future__ import annotations

import ctypes
import sys


class AccentPolicy(ctypes.Structure):
    _fields_ = [
        ("AccentState", ctypes.c_uint),
        ("AccentFlags", ctypes.c_uint),
        ("GradientColor", ctypes.c_uint),
        ("AnimationId", ctypes.c_uint),
    ]


class WindowCompositionAttributeData(ctypes.Structure):
    _fields_ = [
        ("Attribute", ctypes.c_uint),
        ("Data", ctypes.POINTER(AccentPolicy)),
        ("SizeOfData", ctypes.c_uint),
    ]


class MARGINS(ctypes.Structure):
    _fields_ = [
        ("cxLeftWidth", ctypes.c_int),
        ("cxRightWidth", ctypes.c_int),
        ("cyTopHeight", ctypes.c_int),
        ("cyBottomHeight", ctypes.c_int),
    ]


ACCENT_ENABLE_TRANSPARENTGRADIENT = 2
ACCENT_ENABLE_BLURBEHIND = 3
ACCENT_ENABLE_ACRYLICBLURBEHIND = 4
WCA_ACCENT_POLICY = 19

DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWCP_ROUND = 2


def _enable_rounded_corners(hwnd: int, dark_mode: bool = True):
    if sys.platform != "win32":
        return
    try:
        dwmapi = ctypes.windll.dwmapi

        corner = ctypes.c_int(DWMWCP_ROUND)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(corner),
            ctypes.sizeof(corner),
        )

        dark = ctypes.c_int(1 if dark_mode else 0)
        dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark),
            ctypes.sizeof(dark),
        )

        margins = MARGINS(1, 1, 1, 1)
        dwmapi.DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))
    except Exception:
        pass


def disable_acrylic(hwnd: int, dark_mode: bool = True):
    """Disable blur but keep native rounded corners and shadow."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        accent = AccentPolicy()
        accent.AccentState = ACCENT_ENABLE_TRANSPARENTGRADIENT
        accent.AccentFlags = 2
        accent.GradientColor = 0x01000000

        data = WindowCompositionAttributeData()
        data.Attribute = WCA_ACCENT_POLICY
        data.Data = ctypes.pointer(accent)
        data.SizeOfData = ctypes.sizeof(accent)

        user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))
        _enable_rounded_corners(hwnd, dark_mode=dark_mode)
    except Exception:
        pass


def enable_acrylic(hwnd: int, tint_color: int = 0x40202020, dark_mode: bool = True) -> bool:
    """Enable acrylic (with blur fallback) on frameless window."""
    if sys.platform != "win32":
        return False

    try:
        user32 = ctypes.windll.user32
        for state in [ACCENT_ENABLE_ACRYLICBLURBEHIND, ACCENT_ENABLE_BLURBEHIND]:
            accent = AccentPolicy()
            accent.AccentState = state
            accent.AccentFlags = 2
            accent.GradientColor = tint_color

            data = WindowCompositionAttributeData()
            data.Attribute = WCA_ACCENT_POLICY
            data.Data = ctypes.pointer(accent)
            data.SizeOfData = ctypes.sizeof(accent)

            if user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data)):
                _enable_rounded_corners(hwnd, dark_mode=dark_mode)
                return True
        return False
    except Exception:
        return False
