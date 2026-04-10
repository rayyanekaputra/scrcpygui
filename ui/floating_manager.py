"""Floating manager for screenshot and floating widget behavior.

This module keeps floating window lifecycle and screenshot notifications
in a dedicated helper class while still allowing access to the main app
instance via self.app.
"""

import threading
import tkinter as tk
import customtkinter as ctk  # type: ignore
from tkinter import messagebox
import os
from datetime import datetime

from core.adb_manager import capture_screenshot
import core.adb_manager as adb_manager
from ui.ui_constants import FN, FNM, FS


class FloatingManager:
    def __init__(self, app):
        self.app = app

    def _float_live_mode(self, aktif):
        fw = self.app.float_win
        if fw is None:
            return
        if aktif:
            fw.attributes("-alpha", 0.0)
            fw.bind("<Enter>", lambda e, fw=fw: fw.attributes("-alpha", 0.92))
            fw.bind("<Leave>", lambda e, fw=fw: fw.attributes("-alpha", 0.0))
        else:
            fw.unbind("<Enter>"); fw.unbind("<Leave>"); fw.attributes("-alpha", 1.0)

    def _build_floating(self):
        self.app.float_win = ctk.CTkToplevel(self.app)
        fw = self.app.float_win
        fw.overrideredirect(True); fw.attributes("-topmost", True)
        fw.configure(fg_color=adb_manager.CARD)
        sw = self.app.winfo_screenwidth(); sh = self.app.winfo_screenheight()
        fw.geometry(f"154x44+{(sw-154)//2}+{sh-80}")
        row = tk.Frame(fw, bg=adb_manager.CARD); row.pack(fill="both", expand=True)
        drag = tk.Label(row, text="⠿", bg=adb_manager.CARD, fg=adb_manager.BDR,
                        font=(FNM, 11), cursor="fleur", padx=6)
        drag.pack(side="left", fill="y")
        drag.bind("<ButtonPress-1>", lambda e: setattr(self.app, "_dx", e.x) or setattr(self.app, "_dy", e.y))
        drag.bind("<B1-Motion>", lambda e: fw.geometry(
            f"+{fw.winfo_x()+e.x-self.app._dx}+{fw.winfo_y()+e.y-self.app._dy}"))
        tk.Frame(row, bg=adb_manager.BDR, width=1).pack(side="left", fill="y")
        self.app.float_btn_toggle = ctk.CTkButton(row, text="▶", command=self.app._toggle,
            width=52, height=44, fg_color=adb_manager.CARD, hover_color=adb_manager.CARD2,
            text_color=adb_manager.GRN, font=ctk.CTkFont(FNM, FS(16), "bold"), corner_radius=0)
        self.app.float_btn_toggle.pack(side="left")
        tk.Frame(row, bg=adb_manager.BDR, width=1).pack(side="left", fill="y")
        ctk.CTkButton(row, text="📷", command=self.app._screenshot,
            width=52, height=44, fg_color=adb_manager.CARD, hover_color=adb_manager.CARD2,
            text_color=adb_manager.YEL, font=ctk.CTkFont(FNM, FS(16)), corner_radius=0).pack(side="left")
        if not self.app.V["show_floating"].get():
            fw.withdraw()

    def _toggle_floating_visibility(self):
        if self.app.float_win is None:
            return
        self.app.float_win.deiconify() if self.app.V["show_floating"].get() else self.app.float_win.withdraw()

    def _screenshot(self):
        targets = list(self.app.running_devs)
        if not targets:
            dev = self.app.V["device"].get()
            if dev and "no devices" not in dev:
                targets = [dev.split()[0]]
        if not targets:
            messagebox.showwarning("No Device", "No device connected!")
            return

        folder = os.path.expanduser("~/Pictures/scrcpy-screenshots")
        os.makedirs(folder, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        results = {}
        lock = threading.Lock()
        remaining = [len(targets)]

        def _capture_one(serial):
            path = os.path.join(folder, f"ss_{serial}_{ts}.png")
            ok, message = capture_screenshot(serial, path)
            if ok:
                self.app._log(f"→ Screenshot saved: {message}")
                with lock:
                    results[serial] = message
            else:
                self.app._log(f"ERROR screenshot {serial}: {message}")
                with lock:
                    results[serial] = None
            with lock:
                remaining[0] -= 1
                if remaining[0] == 0:
                    self.app.after(0, lambda: self._flash_screenshot_multi(results))

        for serial in targets:
            threading.Thread(target=_capture_one, args=(serial,), daemon=True).start()

    def _flash_screenshot_multi(self, results: dict):
        ok = [s for s, p in results.items() if p]
        total = len(results)
        try:
            fw = self.app.float_win
            if fw is None:
                raise AttributeError
            fx = fw.winfo_x(); fy = fw.winfo_y()
        except Exception:
            fx = self.app.winfo_screenwidth() // 2; fy = self.app.winfo_screenheight() - 120

        toast = ctk.CTkToplevel(self.app)
        toast.overrideredirect(True); toast.attributes("-topmost", True)
        toast.configure(fg_color=adb_manager.CARD)
        fr = ctk.CTkFrame(toast, fg_color=adb_manager.CARD, corner_radius=10, border_width=1,
                          border_color=adb_manager.GRN if ok else adb_manager.RED)
        fr.pack(padx=2, pady=2)
        title = f"✓ {len(ok)}/{total} screenshot(s) saved" if ok else "✗ Screenshot failed"
        ctk.CTkLabel(fr, text=title, font=ctk.CTkFont(FN, FS(10), "bold"),
                     text_color=adb_manager.GRN if ok else adb_manager.RED,
                     fg_color="transparent", padx=14, pady=8).pack()
        for serial, path in results.items():
            color = adb_manager.DIM if path else adb_manager.RED
            label = os.path.basename(path) if path else f"{serial} — failed"
            ctk.CTkLabel(fr, text=label, font=ctk.CTkFont(FN, FS(8)),
                         text_color=color, fg_color="transparent", padx=14, pady=2).pack(anchor="w")
        toast.update_idletasks()
        tw, th = toast.winfo_width(), toast.winfo_height()
        toast.geometry(f"+{fx-max(0,tw-60)}+{fy-th-8}")
        self.app.after(3000, lambda: toast.destroy() if toast.winfo_exists() else None)
