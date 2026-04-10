"""Tab Settings — tools, theme, preset, dan about."""

import customtkinter as ctk  # type: ignore
from datetime import datetime
from core.adb_manager import FN, FNM
import core.adb_manager as adb_manager
from ui.ui_constants import FS
from ui.tabs.base_tab import section


def build(app) -> None:
    """
    Bangun isi tab Settings dan set atribut di app:
        app.lbl_cur_scale    — label persentase UI scale saat ini
        app.btn_theme_dark   — tombol pilih tema dark
        app.btn_theme_light  — tombol pilih tema light
        app._preset_cards    — dict card preset {nama: (card, warna)}
        app.btn_recheck_deps — tombol cek ulang dependensi
        app._dep_summary_lbl — label ringkasan status dep
        app._dep_rows        — dict row dep (kompatibilitas _update_dep_ui)
    """
    tab = app.tabview.tab("⚙️  Settings")
    left  = ctk.CTkFrame(tab, fg_color=adb_manager.BG)
    left.pack(side="left", fill="both", expand=True, padx=(0, 8))
    right = ctk.CTkFrame(tab, fg_color=adb_manager.BG)
    right.pack(side="left", fill="both", expand=True)

    # ── Kiri: Tools ───────────────────────────────────────────────────────────
    section(left, "TOOLS")
    for label, key in [
        ("Floating Widget", "show_floating"),
        ("Device Monitor",  "show_monitor"),
        ("Log Panel",       "log_visible"),
    ]:
        row = ctk.CTkFrame(left, fg_color=adb_manager.BG)
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=label, width=150, anchor="w",
                     font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.TEXT, fg_color=adb_manager.BG).pack(side="left")
        ctk.CTkSwitch(row, text="Show", variable=app.V[key],
            font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BDR,
            progress_color=adb_manager.ACC, button_color=adb_manager.CARD, button_hover_color=adb_manager.CARD2).pack(side="left")

    # Minimize to Tray
    row_t = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    row_t.pack(fill="x", pady=4)
    ctk.CTkLabel(row_t, text="Minimize to Tray", width=150, anchor="w",
                 font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.TEXT, fg_color=adb_manager.BG).pack(side="left")
    ctk.CTkSwitch(row_t, text="On close", variable=app.V["minimize_to_tray"],
        font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BDR,
        progress_color=adb_manager.ACC, button_color=adb_manager.CARD, button_hover_color=adb_manager.CARD2).pack(side="left")

    # UI Scale
    row_sc = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    row_sc.pack(fill="x", pady=4)
    ctk.CTkLabel(row_sc, text="UI Scale", width=150, anchor="w",
                 font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.TEXT, fg_color=adb_manager.BG).pack(side="left")
    cur_scale = app.cfg.get("ui_scale", 1.0)
    app.lbl_cur_scale = ctk.CTkLabel(
        row_sc, text=f"{cur_scale:.0%}", width=48, anchor="w",
        font=ctk.CTkFont(FNM, FS(10), "bold"), text_color=adb_manager.ACC, fg_color="transparent"
    )
    app.lbl_cur_scale.pack(side="left", padx=(0, 8))
    ctk.CTkButton(
        row_sc, text="↺ Re-detect", command=app._rescale_ui,
        width=100, height=26, fg_color=adb_manager.CARD2, hover_color=adb_manager.BDR,
        text_color=adb_manager.DIM, font=ctk.CTkFont(FN, FS(9)),
        border_width=1, border_color=adb_manager.BDR, corner_radius=6
    ).pack(side="left")

    # Theme
    row_th = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    row_th.pack(fill="x", pady=4)
    ctk.CTkLabel(row_th, text="Theme", width=150, anchor="w",
                 font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.TEXT, fg_color=adb_manager.BG).pack(side="left")
    app.btn_theme_dark = ctk.CTkButton(
        row_th, text="🌙 Dark", command=lambda: app._switch_theme("dark"),
        width=80, height=28,
        fg_color=adb_manager.ACC if app.V["theme"].get() == "dark" else adb_manager.CARD,
        hover_color="#0060cc", text_color="white",
        font=ctk.CTkFont(FN, FS(10), "bold"),
        border_width=1, border_color=adb_manager.BDR, corner_radius=8
    )
    app.btn_theme_dark.pack(side="left", padx=(0, 6))
    app.btn_theme_light = ctk.CTkButton(
        row_th, text="☀️ Light", command=lambda: app._switch_theme("light"),
        width=80, height=28,
        fg_color=adb_manager.ACC if app.V["theme"].get() == "light" else adb_manager.CARD,
        hover_color="#0060cc",
        text_color="white" if app.V["theme"].get() == "light" else adb_manager.DIM,
        font=ctk.CTkFont(FN, FS(10), "bold"),
        border_width=1, border_color=adb_manager.BDR, corner_radius=8
    )
    app.btn_theme_light.pack(side="left")

    # ── Quick Preset cards ────────────────────────────────────────────────────
    section(left, "QUICK PRESET")
    preset_frame = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    preset_frame.pack(fill="x", pady=(6, 0))
    app._preset_cards = {}
    for pname, icon, color in [
        ("Performance", "🎮", adb_manager.ACC),
        ("Balanced",    "⚡", "#ff9f0a"),
        ("Saver",       "🍃", adb_manager.GRN),
    ]:
        card = ctk.CTkFrame(preset_frame, fg_color=adb_manager.CARD, corner_radius=12,
                            border_width=2, border_color=adb_manager.BDR, width=88, height=68)
        card.pack(side="left", padx=(0, 8))
        card.pack_propagate(False)
        ctk.CTkLabel(card, text=icon, font=ctk.CTkFont(FN, FS(20)),
                     fg_color="transparent", text_color=color).pack(pady=(10, 0))
        ctk.CTkLabel(card, text=pname, font=ctk.CTkFont(FN, FS(9), "bold"),
                     fg_color="transparent", text_color=adb_manager.TEXT).pack()
        for w in [card] + card.winfo_children():
            w.bind("<Button-1>", lambda e, n=pname: app._apply_preset(n))
            w.configure(cursor="hand2")
        app._preset_cards[pname] = (card, color)

    # ── Preset actions ────────────────────────────────────────────────────────
    section(left, "PRESET")
    btn_row = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    btn_row.pack(fill="x", pady=(4, 0))
    for txt, cmd in [
        ("💾 Save",  app._save),
        ("📋 Copy",  app._copy_cmd),
        ("🔄 Reset", app._reset_config),
    ]:
        ctk.CTkButton(
            btn_row, text=txt, command=cmd, height=32,
            fg_color=adb_manager.CARD, hover_color=adb_manager.CARD2, text_color=adb_manager.TEXT,
            font=ctk.CTkFont(FN, FS(9)),
            border_width=1, border_color=adb_manager.BDR, corner_radius=8
        ).pack(side="left", padx=(0, 6))

    # ── Kanan: About & Dependencies ───────────────────────────────────────────
    section(right, "ABOUT")
    af = ctk.CTkFrame(right, fg_color=adb_manager.CARD, corner_radius=10,
                      border_width=1, border_color=adb_manager.BDR)
    af.pack(fill="x", pady=4)

    ctk.CTkLabel(af, text="ScrcpyGUI",
                 font=ctk.CTkFont(FN, FS(15), "bold"),
                 text_color=adb_manager.TEXT, fg_color=adb_manager.CARD).pack(anchor="w", padx=14, pady=(10, 0))
    ctk.CTkLabel(af, text="Beta  ·  Built for Android Casting",
                 font=ctk.CTkFont(FN, FS(9)), text_color=adb_manager.DIM, fg_color=adb_manager.CARD).pack(
                     anchor="w", padx=14, pady=(2, 8))
    ctk.CTkFrame(af, fg_color=adb_manager.BDR, height=1, corner_radius=0).pack(fill="x", padx=12)

    # Dep header + check button
    dep_hdr = ctk.CTkFrame(af, fg_color=adb_manager.CARD)
    dep_hdr.pack(fill="x", padx=12, pady=(8, 8))
    ctk.CTkLabel(dep_hdr, text="DEPENDENCIES",
                 font=ctk.CTkFont(FN, FS(8), "bold"),
                 text_color=adb_manager.DIM, fg_color=adb_manager.CARD).pack(side="left")
    app.btn_recheck_deps = ctk.CTkButton(
        dep_hdr, text="↺ Check All", command=app._show_deps_popup,
        width=90, height=24, fg_color=adb_manager.ACC, hover_color="#0060cc",
        text_color="white", font=ctk.CTkFont(FN, FS(8), "bold"), corner_radius=6
    )
    app.btn_recheck_deps.pack(side="right")

    app._dep_summary_lbl = ctk.CTkLabel(
        af, text="Click ↺ Check All to verify",
        font=ctk.CTkFont(FN, FS(8)), text_color=adb_manager.DIM, fg_color=adb_manager.CARD, anchor="w"
    )
    app._dep_summary_lbl.pack(anchor="w", padx=14, pady=(0, 8))
    app._dep_rows = {}  # kompatibilitas dengan _update_dep_ui

    ctk.CTkFrame(af, fg_color=adb_manager.BDR, height=1, corner_radius=0).pack(
        fill="x", padx=12, pady=(8, 0))

    # Footer
    footer_frame = ctk.CTkFrame(af, fg_color=adb_manager.CARD)
    footer_frame.pack(fill="x", padx=12, pady=(8, 8))
    ctk.CTkLabel(
        footer_frame,
        text=f"© {datetime.now().year}  venthereal  —  All rights reserved",
        font=ctk.CTkFont(FN, FS(8)), text_color=adb_manager.DIM, fg_color=adb_manager.CARD
    ).pack(anchor="w", pady=(0, 6))
    ctk.CTkButton(
        footer_frame, text="❤️  Donasi via Trakteer",
        command=app._show_donate_dialog,
        width=160, height=28, fg_color=adb_manager.ACC, hover_color="#0060cc",
        text_color="white", font=ctk.CTkFont(FN, FS(9), "bold"), corner_radius=6
    ).pack(anchor="w")
