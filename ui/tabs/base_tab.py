"""Base Tab class - common functionality for all tabs."""

import customtkinter as ctk  # type: ignore
from core.adb_manager import FN, FNM
import core.adb_manager as adb_manager
from ui.ui_constants import FS


def section(parent, title: str) -> ctk.CTkFrame:
    """
    Buat section header dengan garis pemisah (horizontal layout).
    Fungsi bebas — bisa dipanggil langsung tanpa instance:
        section(parent, "VIDEO SETTINGS")
    """
    frame = ctk.CTkFrame(parent, fg_color=adb_manager.BG)
    frame.pack(fill="x", pady=(12, 6))
    ctk.CTkLabel(
        frame,
        text=title,
        font=ctk.CTkFont(FN, FS(8), "bold"),
        text_color=adb_manager.DIM,
        fg_color=adb_manager.BG
    ).pack(side="left")
    ctk.CTkFrame(frame, fg_color=adb_manager.BDR, height=1, corner_radius=0).pack(
        side="left", fill="x", expand=True, padx=(8, 0), pady=6
    )
    return frame


def combo_ctk(parent, values: list, var, width: int = 120,
              on_change=None) -> ctk.CTkComboBox:
    """
    Buat CTkComboBox dengan styling standar ScrcpyGUI.
    Fungsi bebas — bisa dipanggil langsung tanpa instance.

    Args:
        parent   : Parent widget
        values   : List pilihan combo
        var      : StringVar untuk binding nilai
        width    : Lebar widget (default 120)
        on_change: Callback opsional dipanggil saat nilai berubah,
                   menerima satu argumen (nilai baru). Contoh:
                   on_change=lambda _: app.after(20, app._preview)
    """
    return ctk.CTkComboBox(
        parent,
        values=values,
        variable=var,
        width=width,
        font=ctk.CTkFont(FNM, FS(10)),
        fg_color=adb_manager.CARD,
        border_color=adb_manager.BDR,
        button_color=adb_manager.CARD2,
        button_hover_color=adb_manager.BDR,
        dropdown_fg_color=adb_manager.CARD,
        dropdown_text_color=adb_manager.TEXT,
        text_color=adb_manager.TEXT,
        state="readonly",
        command=on_change,
    )


class BaseTab:
    """Base class providing common tab UI building utilities."""

    def __init__(self, app):
        """Initialize with reference to parent App instance."""
        self.app = app

    def section(self, parent, title: str) -> ctk.CTkFrame:
        """Delegasi ke fungsi module-level section()."""
        return section(parent, title)

    def combo_ctk(self, parent, values: list, var,
                  width: int = 120, on_change=None) -> ctk.CTkComboBox:
        """Delegasi ke fungsi module-level combo_ctk()."""
        return combo_ctk(parent, values, var, width, on_change=on_change)
