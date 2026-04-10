"""UI Helper functions - system detection, DPI scaling, palette management."""

import subprocess
import tkinter as tk
import re
import customtkinter as ctk  # type: ignore
from ui.ui_constants import PALETTE_DARK, PALETTE_LIGHT, set_ui_scale
import core.adb_manager as adb_manager


def detect_system_dpi() -> float:
    """
    Detect DPI from xrandr — robust with value validation and Tk fallback.
    Returns DPI value between 60 and 400, defaults to 96.0.
    """
    try:
        r = subprocess.run(["xrandr"], capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            if " connected" not in line:
                continue
            m = re.search(r"(\d+)mm x (\d+)mm", line)
            rm = re.search(r"(\d{3,4})x(\d{3,4})", line)
            if not m or not rm:
                continue
            w_mm = int(m.group(1))
            w_px = int(rm.group(1))
            if w_mm < 50 or w_mm > 1000:
                continue
            dpi = w_px / (w_mm / 25.4)
            if 60 <= dpi <= 400:
                return dpi
    except Exception:
        pass

    # Fallback: use Tk to detect DPI
    try:
        _root = tk.Tk()
        _root.withdraw()
        dpi = _root.winfo_fpixels("1i")
        _root.destroy()
        if 60 <= dpi <= 400:
            return dpi
    except Exception:
        pass

    return 96.0


def apply_palette(name: str):
    """Apply color palette based on theme name ('dark' or 'light')."""
    p = PALETTE_LIGHT if name == "light" else PALETTE_DARK
    adb_manager.BG = p["BG"]
    adb_manager.CARD = p["CARD"]
    adb_manager.CARD2 = p["CARD2"]
    adb_manager.BDR = p["BDR"]
    adb_manager.TEXT = p["TEXT"]
    adb_manager.DIM = p["DIM"]
    ctk.set_appearance_mode("light" if name == "light" else "dark")
    return p


def configure_ui_scale(scale: float):
    """Configure the global UI scale factor (0.75 to 2.0)."""
    set_ui_scale(scale)
