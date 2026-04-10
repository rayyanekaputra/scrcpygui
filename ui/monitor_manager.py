"""Device monitor helper for ScrcpyGUI.

This module encapsulates monitor window creation, polling, and UI updates.
"""

import threading
import tkinter as tk
import customtkinter as ctk  # type: ignore

from core.adb_manager import fetch_device_stats
import core.adb_manager as adb_manager
from ui.ui_constants import FN, FNM, FS


class MonitorManager:
    def __init__(self, app):
        self.app = app

    def _start_monitor_loop(self):
        self._build_monitor()
        self.app._monitor_running = self.app.V["show_monitor"].get()
        self._poll_monitor()

    def _build_monitor(self):
        self.app.monitor_win = ctk.CTkToplevel(self.app)
        mw = self.app.monitor_win
        mw.overrideredirect(True)
        mw.attributes("-topmost", True)
        mw.configure(fg_color=adb_manager.CARD)
        sw = self.app.winfo_screenwidth()
        sh = self.app.winfo_screenheight()
        mw.geometry(f"180x172+{sw-196}+{sh-230}")

        hdr = tk.Frame(mw, bg=adb_manager.CARD2, height=22)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📊 Monitor", bg=adb_manager.CARD2,
                 fg=adb_manager.DIM, font=(FN, 8, "bold")).pack(side="left", padx=8)
        hdr.bind("<ButtonPress-1>", lambda e: setattr(self.app, "_mx", e.x) or setattr(self.app, "_my", e.y))
        hdr.bind("<B1-Motion>", lambda e: mw.geometry(
            f"+{mw.winfo_x()+e.x-self.app._mx}+{mw.winfo_y()+e.y-self.app._my}"))

        body = ctk.CTkFrame(mw, fg_color=adb_manager.CARD, corner_radius=0)
        body.pack(fill="both", expand=True, padx=6, pady=4)
        self.app.mon_labels = {}
        for key, icon, label in [
            ("battery", "🔋", "Battery"), ("temp", "🌡", "Temp"),
            ("ram", "🧠", "RAM"), ("cpu", "⚡", "CPU"),
            ("ping", "🌐", "Ping"), ("net", "↕", "Network"),
        ]:
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkLabel(row, text=f"{icon} {label}", font=ctk.CTkFont(FN, FS(9)),
                         text_color=adb_manager.DIM, fg_color="transparent",
                         width=72, anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="--", font=ctk.CTkFont(FNM, FS(9), "bold"),
                               text_color=adb_manager.TEXT, fg_color="transparent",
                               anchor="e")
            lbl.pack(side="right")
            self.app.mon_labels[key] = lbl

        if not hasattr(self.app, "_prev_net"):
            self.app._prev_net = None
        if not self.app.V["show_monitor"].get():
            mw.withdraw()

    def _poll_monitor(self):
        try:
            if not self.app.winfo_exists():
                return
        except Exception:
            return

        if self.app.V["show_monitor"].get():
            dev = self.app.V["device"].get()
            if dev and "no devices" not in dev and "Scanning" not in dev:
                serial = dev.split()[0]
                threading.Thread(target=self._fetch_stats, args=(serial,), daemon=True).start()

        self.app._monitor_after_id = self.app.after(5000, self._poll_monitor)

    def _fetch_stats(self, serial: str):
        stats, self.app._prev_net = fetch_device_stats(serial, self.app._prev_net)
        self.app.after(0, lambda: self._update_monitor_ui(stats))

    def _update_monitor_ui(self, stats: dict):
        if not hasattr(self.app, "mon_labels"):
            return
        for key, val in stats.items():
            if key not in self.app.mon_labels:
                continue
            color = adb_manager.TEXT
            if key == "battery":
                try:
                    pct = int(val.replace("%", ""))
                    color = adb_manager.RED if pct < 20 else adb_manager.YEL if pct < 50 else adb_manager.GRN
                except Exception:
                    pass
            elif key == "temp":
                try:
                    t = float(val.replace("°C", ""))
                    color = adb_manager.GRN if t < 40 else adb_manager.YEL if t < 55 else adb_manager.RED
                except Exception:
                    pass
            elif key == "cpu":
                try:
                    pct = float(val.replace("%", ""))
                    color = adb_manager.GRN if pct < 50 else adb_manager.YEL if pct < 80 else adb_manager.RED
                except Exception:
                    pass
            elif key == "ping":
                try:
                    ms = float(val.replace("ms", ""))
                    color = adb_manager.GRN if ms < 50 else adb_manager.YEL if ms < 150 else adb_manager.RED
                except Exception:
                    pass
            self.app.mon_labels[key].configure(text=val, text_color=color)
