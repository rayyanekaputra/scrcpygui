"""Tab TCP/IP — WiFi connection manager."""

import customtkinter as ctk  # type: ignore
from core.adb_manager import FN, FNM
import core.adb_manager as adb_manager
from ui.ui_constants import FS
from ui.tabs.base_tab import section


def build(app) -> None:
    """
    Bangun isi tab TCP/IP dan set atribut di app:
        app.txt_tcpip  — CTkTextbox untuk log TCP/IP
    """
    tab = app.tabview.tab("📶  TCP/IP")
    left  = ctk.CTkFrame(tab, fg_color=adb_manager.BG)
    left.pack(side="left", fill="both", expand=True, padx=(0, 8))
    right = ctk.CTkFrame(tab, fg_color=adb_manager.BG)
    right.pack(side="left", fill="both", expand=True)

    # ── Kiri: Connect via WiFi ────────────────────────────────────────────────
    section(left, "CONNECT VIA WIFI")

    info_frame = ctk.CTkFrame(left, fg_color=adb_manager.CARD2, corner_radius=8,
                              border_width=1, border_color=adb_manager.BDR)
    info_frame.pack(fill="x", pady=(0, 12))
    ctk.CTkLabel(
        info_frame,
        text="Connect phone via USB first, then enable TCP/IP.\n"
             "After that you can disconnect USB and use WiFi.",
        font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.CARD2,
        justify="left", wraplength=340, padx=12, pady=10
    ).pack(fill="x", padx=8, pady=4)

    # Port
    row = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    row.pack(fill="x", pady=4)
    ctk.CTkLabel(row, text="Port", width=150, anchor="w",
                 font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left")
    ctk.CTkEntry(row, textvariable=app.V["tcpip_port"], width=100,
                 fg_color=adb_manager.CARD, border_color=adb_manager.BDR, text_color=adb_manager.TEXT,
                 font=ctk.CTkFont(FNM, FS(10))).pack(side="left")
    ctk.CTkLabel(row, text="(default: 5555)", font=ctk.CTkFont(FN, FS(9)),
                 text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left", padx=8)

    ctk.CTkButton(
        left, text="Step 1: Enable TCP/IP (USB required)",
        command=app._enable_tcpip, height=38,
        fg_color=adb_manager.ACC, hover_color="#0060cc",
        text_color="white", font=ctk.CTkFont(FN, FS(11), "bold"), corner_radius=8
    ).pack(fill="x", pady=(8, 4))

    # Device IP
    row2 = ctk.CTkFrame(left, fg_color=adb_manager.BG)
    row2.pack(fill="x", pady=(12, 4))
    ctk.CTkLabel(row2, text="Device IP", width=150, anchor="w",
                 font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left")
    ctk.CTkEntry(row2, textvariable=app.V["tcpip_host"], width=150,
                 placeholder_text="e.g. 192.168.1.100",
                 fg_color=adb_manager.CARD, border_color=adb_manager.BDR, text_color=adb_manager.TEXT,
                 font=ctk.CTkFont(FNM, FS(10))).pack(side="left", padx=(0, 6))
    ctk.CTkButton(
        row2, text="🔍 Auto", command=app._auto_detect_ip,
        width=80, height=30, fg_color=adb_manager.CARD2, hover_color=adb_manager.BDR,
        text_color=adb_manager.DIM, font=ctk.CTkFont(FN, FS(9), "bold"),
        border_width=1, border_color=adb_manager.BDR, corner_radius=8
    ).pack(side="left")

    ctk.CTkButton(
        left, text="Step 2: Connect via WiFi", command=app._connect_wifi,
        height=38, fg_color=adb_manager.GRN, hover_color="#28a745",
        text_color="white", font=ctk.CTkFont(FN, FS(11), "bold"), corner_radius=8
    ).pack(fill="x", pady=4)

    section(left, "BACK TO USB")
    ctk.CTkButton(
        left, text="Disconnect WiFi & Switch to USB",
        command=app._disconnect_wifi, height=38,
        fg_color=adb_manager.CARD2, hover_color=adb_manager.BDR,
        text_color=adb_manager.TEXT, font=ctk.CTkFont(FN, FS(11)),
        border_width=1, border_color=adb_manager.BDR, corner_radius=8
    ).pack(fill="x", pady=4)

    # ── Kanan: TCP/IP Log ─────────────────────────────────────────────────────
    section(right, "TCP/IP LOG")

    app.txt_tcpip = ctk.CTkTextbox(
        right, height=300,
        fg_color=adb_manager.CARD, text_color=adb_manager.TEXT,
        font=ctk.CTkFont(FNM, FS(9)),
        border_color=adb_manager.BDR, border_width=1, wrap="word"
    )
    app.txt_tcpip.pack(fill="both", expand=True)
    app.txt_tcpip.configure(state="disabled")

    tb = app.txt_tcpip._textbox
    tb.tag_configure("ok",    foreground=adb_manager.GRN)
    tb.tag_configure("error", foreground=adb_manager.RED)
    tb.tag_configure("info",  foreground=adb_manager.ACC)
