#!/usr/bin/env python3
import customtkinter as ctk  # type: ignore
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Optional
import subprocess, threading, os, json, time, re, math
from datetime import datetime

# ── Core & Config Imports ──────────────────────────────────────────────────
from core.config import load_config
from core.adb_manager import (COMPOSITOR_FIXES, detect_audio_monitor, detect_compositor, is_hyprland, check_dependencies, check_optional_dependencies, scan_devices)
import core.adb_manager as adb_manager
from ui.ui_constants import (PALETTE_DARK, PALETTE_LIGHT, ACC, BG, CARD, CARD2, DIM, BDR, FN, FNM, GRN, MODES, PLATFORM_RTMP, RED, TEXT, YEL)

# ── UI Module Imports ──────────────────────────────────────────────────────
from ui.config_manager import ConfigManager
from ui.ui_constants import FS, set_ui_scale
from ui.ui_helpers import detect_system_dpi, apply_palette, configure_ui_scale
from ui.monitor_manager import MonitorManager
from ui.floating_manager import FloatingManager
from ui.wifi_manager import WifiManager
from ui import hidpi_handler, preview_manager, device_manager, scrcpy_runner, live_runner, dep_checker
from ui.tabs.base_tab import BaseTab, section, combo_ctk
from ui.tabs import tab_log, tab_tcpip, tab_mirror, tab_settings, tab_live
from ui.widgets import PreviewCanvas, DeviceBar, DonateDialog
from ui.dialogs import DependencyCheckerDialog, HiDPIDialog

# ── PIL / Pillow for preview canvas ────────────────────────────────────────────
try:
    from PIL import Image, ImageTk, ImageDraw, ImageFont  # type: ignore
    PIL_OK = True
except ImportError:
    PIL_OK = False

PREVIEW_TMP = "/tmp/scrcpygui_preview.png"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg           = load_config()
        self.processes     = {}
        self.running_devs  = set()
        self.dev_rows      = {}
        self.process       = None
        self.ffmpeg_proc   = None
        self.xvfb_proc     = None   # virtual display process for livestream
        self.xvfb_display  = ":99"
        self.running       = False
        self.live_running  = False
        self.key_visible   = False
        self._all_devices  = []
        self._monitor_running = False
        self._monitor_after_id: Optional[str] = None
        self._preview_update_id: Optional[str] = None
        self._preview_capture_running = False
        self._prev_net     = None

        # ── Stream preview state ────────────────────────────────────────────────
        self._preview_active     = False
        self._preview_start_time = None
        self._preview_img_ref    = None   # prevent GC on PhotoImage

        # ── Floating window state ───────────────────────────────────────────────
        self._mx = 0  # mouse x for drag tracking
        self._my = 0  # mouse y for drag tracking
        self._dx = 0  # delta x for window position
        self._dy = 0  # delta y for window position
        self.float_win: Optional[ctk.CTkToplevel] = None
        self.monitor_win: Optional[ctk.CTkToplevel] = None

        # ── UI widgets (optional, may be created dynamically) ──────────────────
        self.btn_toggle_cmd: Optional[ctk.CTkButton] = None
        self.frame_cmd_preview: Optional[ctk.CTkFrame] = None
        self.frame_mode: Optional[ctk.CTkFrame] = None
        self._mode_btns: dict = {}
        self._preset_cards: dict = {}
        self.btn_start: Optional[ctk.CTkButton] = None
        self.btn_start_all: Optional[ctk.CTkButton] = None
        self.lbl_statusbar: Optional[ctk.CTkLabel] = None
        self.txt_log: Optional[ctk.CTkTextbox] = None
        self.frame_log_panel: Optional[ctk.CTkFrame] = None
        self.entry_stream_key: Optional[ctk.CTkEntry] = None
        self.btn_toggle_key: Optional[ctk.CTkButton] = None
        self.frame_custom_url: Optional[ctk.CTkFrame] = None
        self.lbl_stream_key_label: Optional[ctk.CTkLabel] = None
        self.lbl_rtmp: Optional[ctk.CTkLabel] = None
        self.txt_tcpip: Optional[ctk.CTkTextbox] = None
        self._dep_rows: dict = {}
        self._dep_summary_lbl: Optional[ctk.CTkLabel] = None
        self._missing_deps: set = set()
        self._proc_start_times: dict = {}

        self.title("ScrcpyGUI")
        self.configure(fg_color=adb_manager.BG)
        self.resizable(True, True)
        self.minsize(960, 560)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        W = min(1020, sw - 40)
        H = min(680, sh - 110)
        self.geometry(f"{W}x{H}+{(sw-W)//2}+20")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ── Apply saved UI scale before building UI ─────────────────────────
        hidpi_handler.apply_ui_scale(self, self.cfg.get("ui_scale", 1.0))

        self._setup_vars()
        self.config_manager = ConfigManager(self)
        for name in ("_save", "_copy_cmd", "_reset_config", "_load_config", "_load_config_no_theme", "_set_config_vars", "_apply_preset"):
            setattr(self, name, getattr(self.config_manager, name))
        self.wifi_manager = WifiManager(self)
        for name in ("_log_tcpip", "_enable_tcpip", "_auto_detect_ip", "_connect_wifi", "_disconnect_wifi"):
            setattr(self, name, getattr(self.wifi_manager, name))
        self.monitor_manager = MonitorManager(self)
        for name in ("_start_monitor_loop", "_build_monitor", "_poll_monitor", "_fetch_stats", "_update_monitor_ui"):
            setattr(self, name, getattr(self.monitor_manager, name))
        self.floating_manager = FloatingManager(self)
        for name in ("_build_floating", "_screenshot", "_flash_screenshot_multi", "_float_live_mode", "_toggle_floating_visibility"):
            setattr(self, name, getattr(self.floating_manager, name))
        self._load_config()
        self._build_ui()
        self._update_mode_ui(); self._update_rtmp_hint()
        # Splash loading — tampil dulu, defer operasi berat
        self.after(0,    self._show_splash)
        self.after(50,   self._refresh_devices)
        self.after(100,  self._build_floating)
        self.after(300,  lambda: dep_checker.check_deps_startup(self))
        self.after(600,  lambda: hidpi_handler.check_hidpi_startup(self))   # HiDPI detection popup
        self.after(800,  self._start_monitor_loop)

    # ── Stub methods for dynamic manager binding ───────────────────────────────────
    def _save(self, *args, **kwargs):
        pass

    def _copy_cmd(self, *args, **kwargs):
        pass

    def _reset_config(self, *args, **kwargs):
        pass

    def _load_config(self, *args, **kwargs):
        pass

    def _load_config_no_theme(self, *args, **kwargs):
        pass

    def _set_config_vars(self, *args, **kwargs):
        pass

    def _apply_preset(self, *args, **kwargs):
        pass

    def _log_tcpip(self, *args, **kwargs):
        pass

    def _enable_tcpip(self, *args, **kwargs):
        pass

    def _auto_detect_ip(self, *args, **kwargs):
        pass

    def _connect_wifi(self, *args, **kwargs):
        pass

    def _disconnect_wifi(self, *args, **kwargs):
        pass

    def _start_monitor_loop(self, *args, **kwargs):
        pass

    def _build_monitor(self, *args, **kwargs):
        pass

    def _poll_monitor(self, *args, **kwargs):
        pass

    def _fetch_stats(self, *args, **kwargs):
        pass

    def _update_monitor_ui(self, *args, **kwargs):
        pass

    def _build_floating(self, *args, **kwargs):
        pass

    def _screenshot(self, *args, **kwargs):
        pass

    def _flash_screenshot_multi(self, *args, **kwargs):
        pass

    def _float_live_mode(self, *args, **kwargs):
        pass

    def _toggle_floating_visibility(self, *args, **kwargs):
        pass

    # ── HiDPI / UI Scale ───────────────────────────────────────────────────────────
    # ── Splash ───────────────────────────────────────────────────────────────
    def _show_splash(self):
        """Loading bar splash — muncul di atas window utama, hilang otomatis."""
        splash = ctk.CTkToplevel(self)
        splash.overrideredirect(True)
        splash.attributes("-topmost", True)
        splash.configure(fg_color=adb_manager.CARD)

        SW, SH = 320, 148
        sx = self.winfo_x() + (self.winfo_width()  - SW) // 2
        sy = self.winfo_y() + (self.winfo_height() - SH) // 2
        splash.geometry(f"{SW}x{SH}+{sx}+{sy}")

        # Border frame
        fr = ctk.CTkFrame(splash, fg_color=adb_manager.CARD, corner_radius=12,
                          border_width=1, border_color=adb_manager.BDR)
        fr.pack(fill="both", expand=True, padx=2, pady=2)

        # App name
        ctk.CTkLabel(fr, text="ScrcpyGUI",
            font=ctk.CTkFont(FN,FS(16), "bold"), text_color=adb_manager.TEXT,
            fg_color="transparent").pack(pady=(18, 2))
        ctk.CTkLabel(fr, text="Starting up…",
            font=ctk.CTkFont(FN,FS(9)), text_color=adb_manager.DIM,
            fg_color="transparent").pack()

        # Progress bar
        bar = ctk.CTkProgressBar(fr, width=240, height=6,
            fg_color=adb_manager.CARD2, progress_color=adb_manager.ACC, corner_radius=4)
        bar.set(0)
        bar.pack(pady=(14, 4))

        # Step label
        lbl_step = ctk.CTkLabel(fr, text="Initializing…",
            font=ctk.CTkFont(FN,FS(8)), text_color=adb_manager.DIM, fg_color="transparent")
        lbl_step.pack()

        # Steps sesuai defer timing
        steps = [
            (50,  0.25, "Scanning devices…"),
            (100, 0.50, "Building widgets…"),
            (300, 0.75, "Checking dependencies…"),
            (800, 1.00, "Ready!"),
        ]

        def _step(idx):
            if idx >= len(steps): return
            delay, progress, label = steps[idx]
            bar.set(progress)
            lbl_step.configure(text=label)
            if idx < len(steps) - 1:
                splash.after(steps[idx+1][0] - delay, lambda: _step(idx + 1))
            else:
                # Selesai — tutup splash
                splash.after(300, lambda: splash.destroy() if splash.winfo_exists() else None)

        splash.after(50, lambda: _step(0))

    # ── Vars ──────────────────────────────────────────────────────────────────
    def _setup_vars(self):
        self.V = {
            "device":        tk.StringVar(),
            "bitrate":       tk.StringVar(value="8M"),
            "fps":           tk.StringVar(value="60"),
            "resolution":    tk.StringVar(value="(default)"),
            "codec":         tk.StringVar(value="h264"),
            "video_encoder":  tk.StringVar(value="(auto)"),
            "rotation":      tk.StringVar(value="0"),
            "mode":          tk.StringVar(value="Mirror Only"),
            "rec_path":      tk.StringVar(value=os.path.expanduser("~/Videos/scrcpy")),
            "rec_fmt":       tk.StringVar(value="mp4"),
            "no_audio":      tk.BooleanVar(value=False),
            "fullscreen":    tk.BooleanVar(value=False),
            "borderless":    tk.BooleanVar(value=False),
            "always_top":    tk.BooleanVar(value=False),
            "stay_awake":    tk.BooleanVar(value=True),
            "screen_off":    tk.BooleanVar(value=False),
            "view_only":     tk.BooleanVar(value=False),
            "win_title":     tk.StringVar(value="scrcpy"),
            "live_platform": tk.StringVar(value="YouTube"),
            "live_key":      tk.StringVar(value=""),
            "live_bitrate":  tk.StringVar(value="3000k"),
            "live_res":      tk.StringVar(value="1280x720"),
            "live_fps":      tk.StringVar(value="30"),
            "live_mic":      tk.BooleanVar(value=False),
            "live_custom_url": tk.StringVar(value=""),
            "show_floating": tk.BooleanVar(value=True),
            "tcpip_port":    tk.StringVar(value="5555"),
            "tcpip_host":    tk.StringVar(value=""),
            "theme":         tk.StringVar(value="dark"),
            "show_monitor":        tk.BooleanVar(value=True),
            "cmd_preview_visible": tk.BooleanVar(value=False),
            "log_visible":         tk.BooleanVar(value=True),
            "minimize_to_tray":    tk.BooleanVar(value=False),
            # 
            "preview_interval":   tk.StringVar(value="2s"),
            "preview_auto_start": tk.BooleanVar(value=True),
        }
        for v in self.V.values():
            v.trace_add("write", lambda *_: self._schedule_cmd_preview_update())
        self.V["live_platform"].trace_add("write", lambda *_: self.after(20, self._update_rtmp_hint))
        self.V["mode"].trace_add("write",          lambda *_: self.after(20, self._update_mode_ui))
        self.V["show_floating"].trace_add("write",  lambda *_: self.after(20, self._toggle_floating_visibility))
        self.V["show_monitor"].trace_add("write",   lambda *_: self.after(20, self._toggle_monitor_visibility))
        self.V["log_visible"].trace_add("write",    lambda *_: self.after(20, self._toggle_log_panel))

    def _schedule_cmd_preview_update(self):
        if self._preview_update_id is not None:
            try:
                self.after_cancel(self._preview_update_id)
            except Exception:
                pass
        self._preview_update_id = self.after(80, self._run_cmd_preview_update)

    def _run_cmd_preview_update(self):
        self._preview_update_id = None
        preview_manager.update_cmd_preview(self)

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build_ui(self):
        self._build_header()
        self._build_devicebar()
        self.tabview = ctk.CTkTabview(
            self, fg_color=adb_manager.BG,
            segmented_button_fg_color=adb_manager.CARD,
            segmented_button_selected_color=adb_manager.ACC,
            segmented_button_selected_hover_color="#0060cc",
            segmented_button_unselected_color=adb_manager.CARD,
            segmented_button_unselected_hover_color=adb_manager.CARD2,
            text_color=adb_manager.DIM, border_color=adb_manager.BDR, border_width=1)
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(8,8))
        for tab in ["📱  Mirror","🔴  Livestream","📶  TCP/IP","⚙️  Settings","📋  Log"]:
            self.tabview.add(tab)
            self.tabview.tab(tab).configure(fg_color=adb_manager.BG)
        tab_mirror.build(self)
        tab_live.build(self, pil_ok=PIL_OK)
        tab_tcpip.build(self)
        tab_settings.build(self)
        tab_log.build(self)

    # ── Header ────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color=adb_manager.CARD, corner_radius=0, height=52)
        hdr.pack(fill="x"); hdr.pack_propagate(False)
        ctk.CTkLabel(hdr, text="ScrcpyGUI", font=ctk.CTkFont(FN,FS(14),"bold"),
                     text_color=adb_manager.TEXT, fg_color=adb_manager.CARD).pack(side="left", padx=16)
        ctk.CTkLabel(hdr, text="Beta", font=ctk.CTkFont(FN,FS(11)),
                     text_color=adb_manager.DIM, fg_color=adb_manager.CARD).pack(side="left")
        self.lbl_status = ctk.CTkLabel(hdr, text="● Ready",
            font=ctk.CTkFont(FNM,FS(10),"bold"), text_color=adb_manager.DIM,
            fg_color=adb_manager.CARD2, corner_radius=8, padx=12, pady=4)
        self.lbl_status.pack(side="right", padx=16, pady=10)
        # Compositor / display server badge — always visible
        _comp = detect_compositor()
        if _comp and _comp in COMPOSITOR_FIXES:
            _badge_label = COMPOSITOR_FIXES[_comp][2]
            _badge_color = COMPOSITOR_FIXES[_comp][3]
        elif os.environ.get("WAYLAND_DISPLAY"):
            _badge_label = " Wayland"
            _badge_color = "#cba6f7"
        else:
            _badge_label = " X11"
            _badge_color = "#a6e3a1"
        ctk.CTkLabel(hdr, text=_badge_label,
            font=ctk.CTkFont(FN,FS(8),"bold"), text_color=_badge_color,
            fg_color=adb_manager.CARD2, corner_radius=6, padx=8, pady=4
        ).pack(side="right", padx=(0,6), pady=10)
        ctk.CTkFrame(self, fg_color=adb_manager.BDR, height=1, corner_radius=0).pack(fill="x")

    # ── Device bar ────────────────────────────────────────────────────────────
    def _build_devicebar(self):
        bar = ctk.CTkFrame(self, fg_color=adb_manager.BG)
        bar.pack(fill="x", padx=16, pady=(12,4))
        ctk.CTkLabel(bar, text="DEVICE", font=ctk.CTkFont(FN,FS(9),"bold"),
                     text_color=adb_manager.DIM, fg_color=adb_manager.BG).pack(side="left", padx=(0,8))
        self.combo_device = ctk.CTkComboBox(
            bar, values=[], variable=self.V["device"], width=320,
            font=ctk.CTkFont(FNM,FS(10)), fg_color=adb_manager.CARD, border_color=adb_manager.BDR,
            button_color=adb_manager.ACC, dropdown_fg_color=adb_manager.CARD, dropdown_text_color=adb_manager.TEXT,
            text_color=adb_manager.TEXT, state="readonly",
            command=lambda val: device_manager.on_device_selected(self, val))
        self.combo_device.pack(side="left", padx=(0,8))
        ctk.CTkButton(bar, text="↺  Refresh", command=self._refresh_devices,
                      width=110, height=32, fg_color=adb_manager.CARD, hover_color=adb_manager.CARD2,
                      text_color=adb_manager.ACC, font=ctk.CTkFont(FN,FS(10),"bold"),
                      border_width=1, border_color=adb_manager.BDR, corner_radius=8
                      ).pack(side="left", padx=(0,8))
        self.lbl_device_info = ctk.CTkLabel(bar, text="", font=ctk.CTkFont(FN,FS(9)),
                                            text_color=adb_manager.DIM, fg_color=adb_manager.BG)
        self.lbl_device_info.pack(side="left")

    def _refresh_devices(self):
        """Refresh device list via ui.device_manager."""
        device_manager.refresh_devices(self)

    def _build_cmd(self, force_always_on_top: bool = False):
        return scrcpy_runner.build_cmd(self, force_always_on_top=force_always_on_top)

    def _serial_from_label(self, label: str) -> str:
        return scrcpy_runner.serial_from_label(self, label)

    def _toggle(self):
        scrcpy_runner.toggle(self)

    def _start_all(self):
        scrcpy_runner.start_all(self)

    def _start_live(self):
        live_runner.start_live(self)

    def _stop(self):
        live_runner.stop(self)

    def _preview(self):
        preview_manager.update_cmd_preview(self)

    def _preview_placeholder(self):
        preview_manager.preview_placeholder(self)

    def _show_deps_popup(self):
        dep_checker.show_deps_popup(self)

    def _dep_gate_popup(self, missing):
        dep_checker.dep_gate_popup(self, missing)

    def _show_donate_dialog(self):
        DonateDialog(self)

    def _toggle_preview(self):
        preview_manager.toggle_preview(self)

    def _rescale_ui(self):
        hidpi_handler.rescale_ui(self)

    def _switch_theme(self, name: str):
        hidpi_handler.switch_theme(self, name)

    def _rebuild_ui(self):
        hidpi_handler.rebuild_ui(self)


    # ── Tab Live (preview canvas on right panel) ───────────────────────────────

    # ── Tab Settings ──────────────────────────────────────────────────────────

    def _clear_log(self):
        if self.txt_log is None:
            return
        self.txt_log.configure(state="normal")
        self.txt_log.delete("0.0","end")
        self.txt_log.configure(state="disabled")

    # ── Helpers ───────────────────────────────────────────

    def _log(self, text: str, tag: str = ""):
        """Append a log entry to the Log tab and auto-scroll."""
        if self.txt_log is None:
            print(text)
            return

        if not text.endswith("\n"):
            text = text + "\n"

        self.txt_log.configure(state="normal")
        # Use public API instead of private _textbox attribute
        tb = self.txt_log
        insert_tag = None
        if tag:
            insert_tag = tag
        elif text.startswith("$ "):
            insert_tag = "cmd"
        elif text.startswith("→"):
            insert_tag = "ok"
        elif text.upper().startswith("ERROR"):
            insert_tag = "error"

        if insert_tag:
            tb.insert("end", text, insert_tag)
        else:
            tb.insert("end", text)
        # auto scroll to bottom
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _combo_ctk(self, parent, values, var, width=120):
        """Thin wrapper — styling dari base_tab.combo_ctk, callback preview dari App."""
        return combo_ctk(parent, values, var, width,
                         on_change=lambda _: self._schedule_cmd_preview_update())

    def _toggle_key_visibility(self):
        if self.entry_stream_key is None or self.btn_toggle_key is None:
            return
        self.key_visible = not self.key_visible
        self.entry_stream_key.configure(show="" if self.key_visible else "•")
        self.btn_toggle_key.configure(text="🔒 Hide Key" if self.key_visible else "👁  Show Key")

    def _toggle_monitor_visibility(self):
        if self.monitor_win is None:
            return
        if self.V["show_monitor"].get():
            self.monitor_win.deiconify(); self._monitor_running = True
        else:
            self.monitor_win.withdraw(); self._monitor_running = False

    def _toggle_log_panel(self):
        if self.frame_log_panel is None:
            return
        if self.V["log_visible"].get():
            self.frame_log_panel.pack(fill="both", expand=True)
        else:
            self.frame_log_panel.pack_forget()

    def _toggle_cmd_preview(self):
        visible = not self.V["cmd_preview_visible"].get()
        self.V["cmd_preview_visible"].set(visible)
        if self.btn_toggle_cmd:
            self.btn_toggle_cmd.configure(text="▼" if visible else "▶")
        if self.frame_cmd_preview:
            if visible: self.frame_cmd_preview.pack(fill="x", pady=(4,0))
            else:       self.frame_cmd_preview.pack_forget()

    def _update_rtmp_hint(self):
        if self.lbl_rtmp is None or self.frame_custom_url is None or self.lbl_stream_key_label is None:
            return
        plat = self.V["live_platform"].get()
        base = PLATFORM_RTMP.get(plat,"")
        if plat == "Custom":
            self.frame_custom_url.pack(fill="x", pady=(0,4), before=self.lbl_stream_key_label)
            self.lbl_rtmp.pack(anchor="w", pady=(2,0))
            self.lbl_rtmp.configure(text="Final URL = RTMP URL + Stream Key")
        else:
            self.frame_custom_url.pack_forget()
            self.lbl_rtmp.pack_forget()

    def _set_mode(self, mode: str):
        self.V["mode"].set(mode)
        # Only update buttons that exist in this tab's _mode_btns
        for m, card in self._mode_btns.items():
            active = m == mode
            card.configure(fg_color=ACC if active else CARD, border_color=ACC if active else BDR)
            colors = ["white","white"] if active else [DIM, TEXT]
            for i, w in enumerate(card.winfo_children()[:2]):
                try: w.configure(text_color=colors[i])
                except: pass

    def _update_mode_ui(self):
        if self.frame_mode is None:
            return
        for w in self.frame_mode.winfo_children(): w.destroy()
        mode = self.V["mode"].get()
        if mode == "Record":
            self._ui_record(self.frame_mode)
        if not self.running and self.btn_start is not None:
            self.btn_start.configure(text="▶   Start Live" if mode=="Livestream" else "▶   Start")
        self._schedule_cmd_preview_update()

    def _ui_record(self, p):
        ctk.CTkLabel(p, text="Save folder", font=ctk.CTkFont(FN,FS(10)),
                     text_color=DIM, fg_color=BG).pack(anchor="w", pady=(8,2))
        row = ctk.CTkFrame(p, fg_color=BG); row.pack(fill="x", pady=(0,4))
        ctk.CTkEntry(row, textvariable=self.V["rec_path"], width=240,
                     fg_color=CARD, border_color=BDR, text_color=TEXT,
                     font=ctk.CTkFont(FNM,FS(10))).pack(side="left", padx=(0,6))
        ctk.CTkButton(row, text="…", command=self._pick_folder, width=36, height=32,
                      fg_color=CARD2, hover_color=BDR, text_color=ACC,
                      font=ctk.CTkFont(FN,FS(12),"bold"), corner_radius=6).pack(side="left")
        row2 = ctk.CTkFrame(p, fg_color=BG); row2.pack(fill="x", pady=4)
        ctk.CTkLabel(row2, text="Format", width=150, anchor="w",
                     font=ctk.CTkFont(FN,FS(10)), text_color=DIM, fg_color=BG).pack(side="left")
        self._combo_ctk(row2, ["mp4","mkv"], self.V["rec_fmt"], 100).pack(side="left")

    # ── Config ────────────────────────────────────────────────────────────────
    # Config methods are handled by ui.config_manager.ConfigManager

    # ── ADB ───────────────────────────────────────────────────────────────────
    # ── Build command ─────────────────────────────────────────────────────────
    # ── Device Monitor ────────────────────────────────────────────────────────
    # Monitor methods have been moved to ui.monitor_manager.MonitorManager

    # ── TCP/IP ────────────────────────────────────────────────────────────────
    # ── Misc ──────────────────────────────────────────────────────────────────
    def _pick_folder(self):
        d = filedialog.askdirectory(initialdir=self.V["rec_path"].get())
        if d: self.V["rec_path"].set(d)

    # ── Config ────────────────────────────────────────────────────────────────
    # Config methods are handled by ui.config_manager.ConfigManager

    def _on_close(self):
        if self.V["minimize_to_tray"].get():
            self.withdraw(); self._show_tray_toast(); return
        any_running = self.running or self.live_running or len(self.running_devs) > 0
        if any_running:
            if not messagebox.askyesno("Quit","Still running. Stop all and quit?"): return
            live_runner.stop(self)
        else:
            if not messagebox.askyesno("Quit","Are you sure you want to quit ScrcpyGUI?"): return
        self._preview_active  = False
        self._monitor_running = False
        self._destroy_all_windows()
        self.destroy()

    def _show_tray_toast(self):
        try:
            toast = ctk.CTkToplevel(self)
            toast.overrideredirect(True); toast.attributes("-topmost", True)
            toast.configure(fg_color=CARD)
            fr = ctk.CTkFrame(toast, fg_color=CARD, corner_radius=10, border_width=1, border_color=ACC)
            fr.pack(padx=2, pady=2)
            ctk.CTkLabel(fr, text="ScrcpyGUI minimized", font=ctk.CTkFont(FN,FS(10),"bold"),
                         text_color=ACC, fg_color="transparent", padx=14, pady=6).pack()
            ctk.CTkLabel(fr, text="Running in background", font=ctk.CTkFont(FN,FS(9)),
                         text_color=DIM, fg_color="transparent", padx=14, pady=4).pack()
            ctk.CTkButton(fr, text="Show Again",
                          command=lambda: [toast.destroy(), self.deiconify()],
                          width=100, height=28, fg_color=ACC, hover_color="#0060cc",
                          text_color="white", font=ctk.CTkFont(FN,FS(9)), corner_radius=6
                          ).pack(pady=(0,8))
            sw = self.winfo_screenwidth(); sh = self.winfo_screenheight()
            toast.update_idletasks()
            tw, th = toast.winfo_width(), toast.winfo_height()
            toast.geometry(f"+{sw-tw-16}+{sh-th-60}")
            toast.after(5000, lambda: toast.destroy() if toast.winfo_exists() else None)
        except Exception:
            # fallback jika toast tidak bisa dibuat
            pass

    def _destroy_all_windows(self):
        for win in ["float_win","monitor_win"]:
            try:
                w = getattr(self, win, None)
                if w and w.winfo_exists(): w.destroy()
            except: pass

    # ── Floating widget ───────────────────────────────────────────────────────
