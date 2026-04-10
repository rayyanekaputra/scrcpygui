"""Tab Livestream — stream config dan preview canvas."""

import tkinter as tk
import customtkinter as ctk  # type: ignore
from core.adb_manager import (FN, FNM, PLATFORM_RTMP)
import core.adb_manager as adb_manager
from ui.ui_constants import FS
from ui.tabs.base_tab import section

# Dimensi preview canvas (16:9)
PREV_W, PREV_H = 316, 178

# Pilihan stream quality
_STREAM_QUALITY = [
    ("Video bitrate", ["1000k","1500k","2000k","2500k","3000k","4000k","5000k","6000k"], "live_bitrate", "bps"),
    ("Resolution",    ["854x480","1280x720","1920x1080"],                                "live_res",      ""),
    ("Stream FPS",    ["24","25","30","48","60"],                                        "live_fps",      "fps"),
]


def build(app, pil_ok: bool = True) -> None:
    """
    Bangun isi tab Livestream dan set atribut di app:
        app.lbl_stream_key_label — label "Stream Key"
        app.frame_custom_url     — frame RTMP URL (show/hide)
        app.entry_stream_key     — entry stream key (masked)
        app.btn_toggle_key       — tombol show/hide key
        app.lbl_rtmp             — label hint RTMP
        app.btn_start_live       — tombol Start Livestream
        app.preview_outer        — frame container canvas
        app.preview_canvas       — tk.Canvas preview
        app.lbl_preview_time     — label elapsed time
        app.lbl_preview_status   — label status preview
        app.lbl_preview_res      — label resolusi frame
        app.btn_preview_toggle   — tombol Capture/Stop
        app.txt_cmd_live         — textbox dummy (hidden)
    """
    tab = app.tabview.tab("🔴  Livestream")
    left  = ctk.CTkFrame(tab, fg_color=adb_manager.BG)
    left.pack(side="left", fill="both", expand=True, padx=(0, 8))
    right = ctk.CTkFrame(tab, fg_color=adb_manager.BG)
    right.pack(side="left", fill="both", expand=True)

    # ── Kiri: Platform & Stream Key ───────────────────────────────────────────
    section(left, "PLATFORM & STREAM KEY")
    row = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    row.pack(fill="x", pady=4)
    ctk.CTkLabel(row, text="Platform", width=150, anchor="w",
                 font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left")
    app._combo_ctk(row, list(PLATFORM_RTMP.keys()), app.V["live_platform"], 140).pack(side="left")

    app.lbl_stream_key_label = ctk.CTkLabel(
        left, text="Stream Key",
        font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BG)
    app.lbl_stream_key_label.pack(anchor="w", pady=(10, 2))

    # Frame RTMP URL — disembunyikan secara default, muncul saat Custom dipilih
    app.frame_custom_url = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    app.frame_custom_url.pack(fill="x", pady=(0, 4))
    ctk.CTkLabel(app.frame_custom_url, text="RTMP URL",
                 font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(
                     anchor="w", pady=(0, 2))
    ctk.CTkEntry(
        app.frame_custom_url, textvariable=app.V["live_custom_url"],
        placeholder_text="rtmp://your-server.com/live/",
        fg_color=adb_manager.CARD, border_color=adb_manager.BDR, text_color=adb_manager.TEXT,
        font=ctk.CTkFont(FNM, FS(10))
    ).pack(fill="x")
    app.frame_custom_url.pack_forget()

    app.entry_stream_key = ctk.CTkEntry(
        left, textvariable=app.V["live_key"],
        show="•", fg_color=adb_manager.CARD, border_color=adb_manager.BDR,
        text_color=adb_manager.TEXT, font=ctk.CTkFont(FNM, FS(10)))
    app.entry_stream_key.pack(fill="x", pady=(0, 4))

    app.btn_toggle_key = ctk.CTkButton(
        left, text="👁  Show Key", command=app._toggle_key_visibility,
        width=120, height=28, fg_color=adb_manager.CARD2, hover_color=adb_manager.BDR,
        text_color=adb_manager.DIM, font=ctk.CTkFont(FN, FS(9)),
        corner_radius=6, border_width=1, border_color=adb_manager.BDR)
    app.btn_toggle_key.pack(anchor="w", pady=(0, 4))

    app.lbl_rtmp = ctk.CTkLabel(
        left, text="", font=ctk.CTkFont(FN, FS(8)),
        text_color=adb_manager.DIM, fg_color=adb_manager.BG, wraplength=340, justify="left")
    app.lbl_rtmp.pack(anchor="w", pady=(2, 0))

    # ── Stream Quality ────────────────────────────────────────────────────────
    section(left, "STREAM QUALITY")
    for label, vals, key, unit in _STREAM_QUALITY:
        row = ctk.CTkFrame(left, fg_color=adb_manager.BG)
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=label, width=150, anchor="w",
                     font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left")
        app._combo_ctk(row, vals, app.V[key], 130).pack(side="left", padx=(0, 6))
        if unit:
            ctk.CTkLabel(row, text=unit, font=ctk.CTkFont(FN, FS(9)),
                         text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left")

    ctk.CTkCheckBox(
        left, text="🎙  Enable Microphone", variable=app.V["live_mic"],
        font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.TEXT,
        fg_color=adb_manager.ACC, hover_color="#0060cc",
        checkmark_color=adb_manager.TEXT, border_color=adb_manager.BDR, width=20, height=20,
        command=lambda: app.after(20, app._preview)
    ).pack(anchor="w", pady=(12, 0))

    # ── Tombol Start ──────────────────────────────────────────────────────────
    ctk.CTkFrame(left, fg_color=adb_manager.BG, height=20).pack()
    app.btn_start_live = ctk.CTkButton(
        left, text="🔴  Start Livestream",
        command=lambda: (app.V["mode"].set("Livestream"), app._toggle()),
        height=38, fg_color=adb_manager.RED, hover_color="#cc0000",
        text_color="white", font=ctk.CTkFont(FN, FS(11), "bold"), corner_radius=8)
    app.btn_start_live.pack(fill="x")

    # ── Kanan: Stream Preview Canvas ──────────────────────────────────────────
    section(right, "STREAM PREVIEW")

    # Peringatan jika Pillow tidak tersedia
    if not pil_ok:
        warn = ctk.CTkFrame(right, fg_color=adb_manager.CARD2, corner_radius=6,
                            border_width=1, border_color=adb_manager.YEL)
        warn.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(warn, text="⚠  Pillow is optional",
                     font=ctk.CTkFont(FN, FS(9), "bold"), text_color=adb_manager.YEL,
                     fg_color="transparent", padx=10, pady=4).pack(side="left")
        ctk.CTkLabel(warn, text="Preview may still work using Tk PNG support",
                     font=ctk.CTkFont(FNM, FS(9)), text_color=adb_manager.DIM,
                     fg_color="transparent", padx=6).pack(side="left")

    # Canvas container (16:9)
    app.preview_outer = ctk.CTkFrame(right, fg_color=adb_manager.CARD, corner_radius=8,
                                     border_width=1, border_color=adb_manager.BDR)
    app.preview_outer.pack(pady=(2, 0))
    app.preview_canvas = tk.Canvas(
        app.preview_outer, width=PREV_W, height=PREV_H,
        bg="#111111", highlightthickness=0, cursor="crosshair")
    app.preview_canvas.pack(padx=2, pady=2)
    app._preview_placeholder()

    ctk.CTkFrame(right, fg_color=adb_manager.BG, height=4).pack(fill="x")

    # Stats bar di bawah canvas
    stats_bar = ctk.CTkFrame(right, fg_color=adb_manager.CARD2, corner_radius=6,
                             border_width=1, border_color=adb_manager.BDR, height=26)
    stats_bar.pack(fill="x")
    stats_bar.pack_propagate(False)

    app.lbl_preview_time = ctk.CTkLabel(
        stats_bar, text="--:--:--",
        font=ctk.CTkFont(FNM, FS(9), "bold"), text_color=adb_manager.DIM, fg_color="transparent")
    app.lbl_preview_time.pack(side="left", padx=8)

    app.lbl_preview_status = ctk.CTkLabel(
        stats_bar, text="idle",
        font=ctk.CTkFont(FN, FS(8)), text_color=adb_manager.DIM, fg_color="transparent")
    app.lbl_preview_status.pack(side="left")

    app.lbl_preview_res = ctk.CTkLabel(
        stats_bar, text="",
        font=ctk.CTkFont(FNM, FS(8)), text_color=adb_manager.DIM, fg_color="transparent")
    app.lbl_preview_res.pack(side="right", padx=8)

    # Preview controls
    ctrl = ctk.CTkFrame(right, fg_color=adb_manager.BG)
    ctrl.pack(fill="x", pady=(6, 0))

    app.btn_preview_toggle = ctk.CTkButton(
        ctrl, text="📷  Capture", command=app._toggle_preview,
        width=110, height=28, fg_color=adb_manager.CARD2, hover_color=adb_manager.BDR,
        text_color=adb_manager.DIM, font=ctk.CTkFont(FN, FS(9), "bold"),
        border_width=1, border_color=adb_manager.BDR, corner_radius=8)
    app.btn_preview_toggle.pack(side="left", padx=(0, 8))

    ctk.CTkLabel(ctrl, text="Interval", font=ctk.CTkFont(FN, FS(9)),
                 text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left", padx=(0, 4))
    app._combo_ctk(ctrl, ["1s","2s","3s","5s"],
                   app.V["preview_interval"], 68).pack(side="left", padx=(0, 10))

    ctk.CTkCheckBox(
        ctrl, text="Auto", variable=app.V["preview_auto_start"],
        font=ctk.CTkFont(FN, FS(9)), text_color=adb_manager.DIM,
        fg_color=adb_manager.ACC, hover_color="#0060cc",
        checkmark_color=adb_manager.TEXT, border_color=adb_manager.BDR,
        width=16, height=16).pack(side="left")

    # Dummy hidden widget agar _preview() tidak error
    app.txt_cmd_live = ctk.CTkTextbox(right, height=1, fg_color=adb_manager.BG, border_width=0)
    app.txt_cmd_live.pack_forget()
    app.txt_cmd_live.configure(state="disabled")
