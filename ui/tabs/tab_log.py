"""Tab Log — ADB & FFmpeg log viewer."""

import customtkinter as ctk  # type: ignore
from core.adb_manager import FN, FNM
import core.adb_manager as adb_manager
from ui.ui_constants import FS


def build(app) -> None:
    """
    Bangun isi tab Log dan set atribut di app:
        app.frame_log_panel  — frame yang bisa di-show/hide
        app.txt_log          — CTkTextbox untuk output log
    """
    tab = app.tabview.tab("📋  Log")

    # ── Toolbar ───────────────────────────────────────────────────────────────
    bar = ctk.CTkFrame(tab, fg_color=adb_manager.BG)
    bar.pack(fill="x", pady=(0, 8))

    ctk.CTkLabel(
        bar, text="ADB & FFMPEG LOG",
        font=ctk.CTkFont(FN, FS(9), "bold"),
        text_color=adb_manager.DIM, fg_color=adb_manager.BG
    ).pack(side="left")

    ctk.CTkButton(
        bar, text="🗑  Clear", command=app._clear_log,
        width=80, height=28,
        fg_color=adb_manager.CARD2, hover_color=adb_manager.BDR,
        text_color=adb_manager.DIM, font=ctk.CTkFont(FN, FS(9)),
        border_width=1, border_color=adb_manager.BDR, corner_radius=6
    ).pack(side="right")

    # ── Log panel (bisa disembunyikan) ────────────────────────────────────────
    app.frame_log_panel = ctk.CTkFrame(tab, fg_color=adb_manager.BG)

    app.txt_log = ctk.CTkTextbox(
        app.frame_log_panel,
        fg_color=adb_manager.CARD,
        text_color="#555555",
        font=ctk.CTkFont(FNM, FS(9)),
        border_color=adb_manager.BDR,
        border_width=1,
        wrap="word"
    )
    app.txt_log.pack(fill="both", expand=True)
    app.txt_log.configure(state="disabled")

    # Warna tag untuk kategori log
    tb = app.txt_log._textbox
    tb.tag_configure("error", foreground=adb_manager.RED)
    tb.tag_configure("ok",    foreground=adb_manager.GRN)
    tb.tag_configure("cmd",   foreground=adb_manager.YEL)
    tb.tag_configure("redup", foreground="#aaaaaa")

    if app.V["log_visible"].get():
        app.frame_log_panel.pack(fill="both", expand=True)
