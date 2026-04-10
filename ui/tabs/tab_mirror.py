"""Tab Mirror — screen mirroring settings."""

import customtkinter as ctk  # type: ignore
from datetime import datetime
from core.adb_manager import FN, FNM
import core.adb_manager as adb_manager
from ui.ui_constants import FS
from ui.tabs.base_tab import section

# Pilihan untuk combo video settings
_VIDEO_SETTINGS = [
    ("Bit rate",       ["1M","2M","4M","6M","8M","10M","12M","16M","20M","25M"], "bitrate",     "Mbps"),
    ("Max FPS",        ["15","24","30","45","60","90","120"],                     "fps",         "fps"),
    ("Max resolution", ["(default)","480","720","1080","1280","1440","1920"],     "resolution",  "px"),
    ("Codec",          ["h264","h265","av1"],                                     "codec",       ""),
    ("Rotation",       ["0","90","180","270"],                                    "rotation",    "°"),
]


def build(app) -> None:
    """
    Bangun isi tab Mirror dan set atribut di app:
        app.combo_encoder    — combo untuk memilih encoder
        app.lbl_encoder_hint — label hint encoder
        app._mode_btns       — dict card per mode
        app.frame_mode       — frame konten mode (Record/Mirror)
        app.txt_cmd          — textbox preview command (hidden)
        app.btn_start        — tombol Start/Stop
        app.btn_start_all    — tombol Start All
        app.lbl_statusbar    — label status bar bawah
    """
    tab = app.tabview.tab("📱  Mirror")
    left  = ctk.CTkFrame(tab, fg_color=adb_manager.BG)
    left.pack(side="left", fill="both", expand=True, padx=(0, 8))
    right = ctk.CTkFrame(tab, fg_color=adb_manager.BG)
    right.pack(side="left", fill="both", expand=True)

    # ── Kiri: Video Settings ──────────────────────────────────────────────────
    section(left, "VIDEO SETTINGS")
    for label, vals, key, unit in _VIDEO_SETTINGS:
        row = ctk.CTkFrame(left, fg_color=adb_manager.BG)
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=label, width=150, anchor="w",
                     font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left")
        app._combo_ctk(row, vals, app.V[key], 120).pack(side="left", padx=(0, 6))
        if unit:
            ctk.CTkLabel(row, text=unit, font=ctk.CTkFont(FN, FS(9)),
                         text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left")

    # Video Encoder — diisi dinamis saat device dipilih
    row_enc = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    row_enc.pack(fill="x", pady=4)
    ctk.CTkLabel(row_enc, text="Video Encoder", width=150, anchor="w",
                 font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left")
    app.combo_encoder = app._combo_ctk(row_enc, ["(auto)"], app.V["video_encoder"], 220)
    app.combo_encoder.pack(side="left", padx=(0, 6))
    app.lbl_encoder_hint = ctk.CTkLabel(row_enc, text="",
        font=ctk.CTkFont(FN, FS(8)), text_color=adb_manager.DIM, fg_color=adb_manager.BG)
    app.lbl_encoder_hint.pack(side="left")

    # ── Output Mode cards ─────────────────────────────────────────────────────
    section(left, "OUTPUT MODE")
    mode_cards = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    mode_cards.pack(fill="x", pady=(6, 0))
    app._mode_btns = {}
    for m, icon, label in [("Mirror Only", "📱", "Mirroring"), ("Record", "⏺", "Record")]:
        active = app.V["mode"].get() == m
        card = ctk.CTkFrame(
            mode_cards,
            fg_color=adb_manager.ACC if active else adb_manager.CARD,
            corner_radius=12, border_width=2,
            border_color=adb_manager.ACC if active else adb_manager.BDR,
            width=88, height=68
        )
        card.pack(side="left", padx=(0, 8))
        card.pack_propagate(False)
        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(FN, FS(20)), fg_color="transparent",
                     text_color="white" if active else adb_manager.DIM).pack(pady=(10, 0))
        ctk.CTkLabel(card, text=label, font=ctk.CTkFont(FN, FS(9), "bold"), fg_color="transparent",
                     text_color="white" if active else adb_manager.TEXT).pack()
        for w in [card] + card.winfo_children():
            w.bind("<Button-1>", lambda e, v=m: app._set_mode(v))
            w.configure(cursor="hand2")
        app._mode_btns[m] = card

    app.frame_mode = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    app.frame_mode.pack(fill="x", pady=(10, 0))

    # ── Kanan: Display Options ────────────────────────────────────────────────
    section(right, "DISPLAY OPTIONS")
    options = [
        ("No audio",       "no_audio"),
        ("Fullscreen",     "fullscreen"),
        ("Borderless",     "borderless"),
        ("Always on top",  "always_top"),
        ("Stay awake",     "stay_awake"),
        ("Turn screen off","screen_off"),
        ("View only",      "view_only"),
    ]
    grid = ctk.CTkFrame(right, fg_color=adb_manager.BG)
    grid.pack(fill="x", pady=4)
    for i, (teks, key) in enumerate(options):
        ctk.CTkCheckBox(
            grid, text=teks, variable=app.V[key],
            font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.TEXT,
            fg_color=adb_manager.ACC, hover_color="#0060cc",
            checkmark_color=adb_manager.TEXT, border_color=adb_manager.BDR,
            width=20, height=20,
            command=lambda: app.after(20, app._preview)
        ).grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 20), pady=5)

    # ── Window ────────────────────────────────────────────────────────────────
    section(right, "WINDOW")
    row = ctk.CTkFrame(right, fg_color=adb_manager.BG)
    row.pack(fill="x", pady=3)
    ctk.CTkLabel(row, text="Window title", width=150, anchor="w",
                 font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left")
    ctk.CTkEntry(row, textvariable=app.V["win_title"], width=180,
                 fg_color=adb_manager.CARD, border_color=adb_manager.BDR, text_color=adb_manager.TEXT,
                 font=ctk.CTkFont(FNM, FS(10))).pack(side="left")

    ctk.CTkFrame(right, fg_color=adb_manager.BDR, height=1, corner_radius=0).pack(fill="x", pady=(16, 0))

    # Dummy hidden widget agar _preview() tidak error sebelum tab Live diinit
    app.txt_cmd = ctk.CTkTextbox(right, height=1, fg_color=adb_manager.BG, border_width=0)
    app.txt_cmd.pack_forget()
    app.txt_cmd.configure(state="disabled")

    # ── Tombol Start ──────────────────────────────────────────────────────────
    btn_row = ctk.CTkFrame(right, fg_color=adb_manager.BG)
    btn_row.pack(fill="x", pady=(8, 4))
    app.btn_start = ctk.CTkButton(
        btn_row, text="▶  Start", command=app._toggle,
        height=38, fg_color=adb_manager.ACC, hover_color="#0060cc",
        text_color="white", font=ctk.CTkFont(FN, FS(11), "bold"), corner_radius=8
    )
    app.btn_start.pack(side="left", fill="x", expand=True, padx=(0, 6))
    app.btn_start_all = ctk.CTkButton(
        btn_row, text="▶▶  All", command=app._start_all,
        height=38, fg_color=adb_manager.GRN, hover_color="#28a745", state="disabled",
        text_color="white", font=ctk.CTkFont(FN, FS(11), "bold"), corner_radius=8
    )
    app.btn_start_all.pack(side="left", fill="x", expand=True)

    app.lbl_statusbar = ctk.CTkLabel(
        right, text=f"© {datetime.now().year}  VEN",
        font=ctk.CTkFont(FN, FS(9)), text_color=adb_manager.DIM, fg_color=adb_manager.BG
    )
    app.lbl_statusbar.pack(anchor="center", pady=(0, 4))
