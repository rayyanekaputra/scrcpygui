"""HiDPI & UI Scale handler — deteksi DPI, popup konfirmasi, rebuild UI."""

import threading
import tkinter as tk
import customtkinter as ctk  # type: ignore

from core.adb_manager import FN
import core.adb_manager as adb_manager
from core.config import save_config
from ui.ui_constants import FS
from ui.ui_helpers import detect_system_dpi, apply_palette, configure_ui_scale


def apply_ui_scale(app, scale: float) -> None:
    """Set global UI_SCALE dan resize window sesuai scale."""
    configure_ui_scale(scale)
    base_w, base_h = 960, 560
    app.minsize(round(base_w * scale), round(base_h * scale))
    sw = app.winfo_screenwidth()
    sh = app.winfo_screenheight()
    W = min(round(1020 * scale), sw - 40)
    H = min(round(680  * scale), sh - 110)
    app.geometry(f"{W}x{H}+{(sw-W)//2}+20")


def check_hidpi_startup(app) -> None:
    """Cek DPI sistem — kalau HiDPI dan belum pernah ditanya, tampilkan popup."""
    if app.cfg.get("ui_scale_asked", False):
        return
    def _run():
        dpi = detect_system_dpi()
        if dpi > 120:
            scale = round(dpi / 96.0, 2)
            scale = min(2.0, max(1.0, round(scale * 4) / 4))  # round ke 0.25
            app.after(0, lambda: show_hidpi_popup(app, dpi, scale))
    threading.Thread(target=_run, daemon=True).start()


def show_hidpi_popup(app, dpi: float, suggested_scale: float) -> None:
    """Popup konfirmasi scale untuk HiDPI display."""
    popup = ctk.CTkToplevel(app)
    popup.title("HiDPI Display Detected")
    popup.configure(fg_color=adb_manager.BG)
    popup.resizable(False, False)
    popup.attributes("-topmost", True)
    popup.grab_set()

    popup.update_idletasks()
    pw, ph = 400, 280
    sx = int(app.winfo_x()) + (int(app.winfo_width())  - pw) // 2
    sy = int(app.winfo_y()) + (int(app.winfo_height()) - ph) // 2
    popup.geometry(f"{pw}x{ph}+{sx}+{sy}")

    # Header
    hdr = ctk.CTkFrame(popup, fg_color=adb_manager.CARD, corner_radius=0, height=48)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    ctk.CTkLabel(hdr, text="🖥  HiDPI Display Detected",
        font=ctk.CTkFont(FN, FS(13), "bold"), text_color=adb_manager.ACC,
        fg_color="transparent").pack(side="left", padx=16)

    body = ctk.CTkFrame(popup, fg_color=adb_manager.BG)
    body.pack(fill="both", expand=True, padx=20, pady=12)

    ctk.CTkLabel(body,
        text=f"Your display DPI is {dpi:.0f} (normal = 96). "
             f"UI scale {suggested_scale:.2f}x is recommended.",
        font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM,
        fg_color="transparent", justify="left", wraplength=340,
    ).pack(anchor="w", pady=(0, 16))

    ctk.CTkLabel(body, text="Select UI Scale:",
        font=ctk.CTkFont(FN, FS(9), "bold"), text_color=adb_manager.DIM,
        fg_color="transparent").pack(anchor="w", pady=(0, 8))

    scale_var     = tk.DoubleVar(value=suggested_scale)
    scale_options = [0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
    scale_labels  = ["75%", "100% (default)", "125%", "150%", "175%", "200%"]

    btn_row = ctk.CTkFrame(body, fg_color=adb_manager.BG)
    btn_row.pack(fill="x")
    scale_btns = {}

    def _on_select(val):
        scale_var.set(val)
        for v, lbl in zip(scale_options, scale_labels):
            b = scale_btns.get(v)
            if not b: continue
            active = abs(v - val) < 0.01
            b.configure(
                fg_color=adb_manager.ACC if active else adb_manager.CARD,
                text_color="white" if active else adb_manager.DIM,
                border_color=adb_manager.ACC if active else adb_manager.BDR)

    for val, lbl in zip(scale_options, scale_labels):
        active = abs(val - suggested_scale) < 0.01
        btn = ctk.CTkButton(btn_row, text=lbl,
            width=72, height=28,
            fg_color=adb_manager.ACC if active else adb_manager.CARD,
            hover_color="#0060cc",
            text_color="white" if active else adb_manager.DIM,
            font=ctk.CTkFont(FN, FS(9)),
            border_width=1, border_color=adb_manager.ACC if active else adb_manager.BDR,
            corner_radius=6,
            command=lambda v=val: _on_select(v))
        btn.pack(side="left", padx=(0, 4))
        scale_btns[val] = btn

    ctk.CTkFrame(body, fg_color=adb_manager.BDR, height=1).pack(fill="x", pady=(16, 8))
    act_row = ctk.CTkFrame(body, fg_color=adb_manager.BG)
    act_row.pack(fill="x")

    def _apply():
        scale = scale_var.get()
        app.cfg["ui_scale"] = scale
        app.cfg["ui_scale_asked"] = True
        save_config(app.cfg)
        popup.grab_release(); popup.destroy()
        apply_ui_scale(app, scale)
        app._rebuild_ui()

    def _skip():
        app.cfg["ui_scale_asked"] = True
        save_config(app.cfg)
        popup.grab_release(); popup.destroy()

    ctk.CTkButton(act_row, text="Skip", command=_skip,
        width=80, height=32, fg_color=adb_manager.CARD, hover_color=adb_manager.CARD2,
        text_color=adb_manager.DIM, font=ctk.CTkFont(FN, FS(10)),
        border_width=1, border_color=adb_manager.BDR, corner_radius=8).pack(side="left")

    ctk.CTkButton(act_row, text="✓  Apply Scale", command=_apply,
        width=140, height=32, fg_color=adb_manager.ACC, hover_color="#0060cc",
        text_color="white", font=ctk.CTkFont(FN, FS(10), "bold"),
        corner_radius=8).pack(side="right")


def rescale_ui(app) -> None:
    """Re-detect DPI dan tampilkan popup scale lagi."""
    app.cfg["ui_scale_asked"] = False
    save_config(app.cfg)
    check_hidpi_startup(app)


def switch_theme(app, name: str) -> None:
    """Ganti tema dan rebuild UI."""
    if app.V["theme"].get() == name:
        return
    app.V["theme"].set(name)
    apply_palette(name)
    app._save()
    rebuild_ui(app)


def rebuild_ui(app) -> None:
    """Hancurkan semua widget dan bangun ulang dari nol."""
    current_theme = app.V["theme"].get()
    app._preview_active  = False
    app._monitor_running = False
    if getattr(app, "_monitor_after_id", None):
        try:
            app.after_cancel(app._monitor_after_id)
        except Exception:
            pass
        app._monitor_after_id = None

    for win_attr in ["float_win", "monitor_win"]:
        try:
            w = getattr(app, win_attr, None)
            if w and w.winfo_exists():
                w.destroy()
        except Exception:
            pass

    for w in app.winfo_children():
        try:
            w.destroy()
        except Exception:
            pass

    apply_palette(current_theme)
    app.configure(fg_color=adb_manager.BG)
    app._build_ui()
    app._load_config_no_theme()
    app._refresh_devices()
    app._build_floating()
    app._build_monitor()
    app._monitor_running = app.V["show_monitor"].get()
    app.after(1000, app._poll_monitor)
