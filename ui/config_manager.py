"""Configuration manager for ScrcpyGUI.

This module centralizes config loading, saving, preset application, and safe JSON
file reading so the main window class stays focused on UI layout.
"""

import json
import os
import threading
from tkinter import messagebox

from core.config import CONFIG_FILE, DEFAULT_CONFIG, save_config
from ui.ui_helpers import apply_palette
from ui import scrcpy_runner
import core.adb_manager as adb_manager
from core.adb_manager import PRESETS


class ConfigManager:
    def __init__(self, app):
        self.app = app

    def _safe_load_config(self):
        config = DEFAULT_CONFIG.copy()
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    config.update(data)
        except Exception:
            # If JSON is invalid or file cannot be read, fall back to defaults.
            config = DEFAULT_CONFIG.copy()
        return config

    def _load_config(self):
        self.app.cfg = self._safe_load_config()
        self._set_config_vars(self.app.cfg)
        saved_theme = self.app.cfg.get("theme", "dark")
        self.app.V["theme"].set(saved_theme)
        apply_palette(saved_theme)

    def _load_config_no_theme(self):
        self._set_config_vars(self.app.cfg)
        self.app._update_mode_ui()
        self.app._update_rtmp_hint()

    def _set_config_vars(self, c):
        self.app.V["bitrate"].set(c.get("bitrate", "8M"))
        self.app.V["fps"].set(c.get("max_fps", "60"))
        self.app.V["resolution"].set(c.get("resolution", "(default)"))
        self.app.V["codec"].set(c.get("codec", "h264"))
        self.app.V["video_encoder"].set(c.get("video_encoder", "(auto)"))
        self.app.V["rotation"].set(c.get("rotation", "0"))
        self.app.V["mode"].set(c.get("mode", "Mirror Only"))
        self.app.V["rec_path"].set(c.get("record_path", os.path.expanduser("~/Videos/scrcpy")))
        self.app.V["rec_fmt"].set(c.get("record_format", "mp4"))
        self.app.V["no_audio"].set(c.get("no_audio", False))
        self.app.V["fullscreen"].set(c.get("fullscreen", False))
        self.app.V["borderless"].set(c.get("borderless", False))
        self.app.V["always_top"].set(c.get("always_on_top", False))
        self.app.V["stay_awake"].set(c.get("stay_awake", True))
        self.app.V["screen_off"].set(c.get("turn_screen_off", False))
        self.app.V["view_only"].set(c.get("no_control", False))
        self.app.V["win_title"].set(c.get("window_title", "scrcpy"))
        self.app.V["live_platform"].set(c.get("live_platform", "YouTube"))
        self.app.V["live_key"].set(c.get("live_key", ""))
        self.app.V["live_bitrate"].set(c.get("live_bitrate", "3000k"))
        self.app.V["live_res"].set(c.get("live_resolution", "1280x720"))
        self.app.V["live_fps"].set(c.get("live_fps", "30"))
        self.app.V["live_custom_url"].set(c.get("live_custom_url", ""))
        self.app.V["show_floating"].set(c.get("show_floating", True))
        self.app.V["tcpip_port"].set(c.get("tcpip_port", "5555"))
        self.app.V["tcpip_host"].set(c.get("tcpip_host", ""))
        self.app.V["show_monitor"].set(c.get("show_monitor", True))
        self.app.V["cmd_preview_visible"].set(c.get("cmd_preview_visible", False))
        self.app.V["log_visible"].set(c.get("log_visible", True))
        self.app.V["minimize_to_tray"].set(c.get("minimize_to_tray", False))
        self.app.V["preview_interval"].set(c.get("preview_interval", "2s"))
        self.app.V["preview_auto_start"].set(c.get("preview_auto_start", True))

    def _save(self):
        self.app.cfg.update({
            "bitrate": self.app.V["bitrate"].get(),
            "max_fps": self.app.V["fps"].get(),
            "resolution": self.app.V["resolution"].get(),
            "codec": self.app.V["codec"].get(),
            "video_encoder": self.app.V["video_encoder"].get(),
            "rotation": self.app.V["rotation"].get(),
            "mode": self.app.V["mode"].get(),
            "record_path": self.app.V["rec_path"].get(),
            "record_format": self.app.V["rec_fmt"].get(),
            "no_audio": self.app.V["no_audio"].get(),
            "fullscreen": self.app.V["fullscreen"].get(),
            "borderless": self.app.V["borderless"].get(),
            "always_on_top": self.app.V["always_top"].get(),
            "stay_awake": self.app.V["stay_awake"].get(),
            "turn_screen_off": self.app.V["screen_off"].get(),
            "no_control": self.app.V["view_only"].get(),
            "window_title": self.app.V["win_title"].get(),
            "live_platform": self.app.V["live_platform"].get(),
            "live_key": self.app.V["live_key"].get(),
            "live_bitrate": self.app.V["live_bitrate"].get(),
            "live_resolution": self.app.V["live_res"].get(),
            "live_fps": self.app.V["live_fps"].get(),
            "show_floating": self.app.V["show_floating"].get(),
            "tcpip_port": self.app.V["tcpip_port"].get(),
            "tcpip_host": self.app.V["tcpip_host"].get(),
            "live_custom_url": self.app.V["live_custom_url"].get(),
            "theme": self.app.V["theme"].get(),
            "show_monitor": self.app.V["show_monitor"].get(),
            "cmd_preview_visible": self.app.V["cmd_preview_visible"].get(),
            "log_visible": self.app.V["log_visible"].get(),
            "minimize_to_tray": self.app.V["minimize_to_tray"].get(),
            "preview_interval": self.app.V["preview_interval"].get(),
            "preview_auto_start": self.app.V["preview_auto_start"].get(),
            "ui_scale": self.app.cfg.get("ui_scale", 1.0),
            "ui_scale_asked": self.app.cfg.get("ui_scale_asked", False),
        })
        save_config(self.app.cfg)
        if self.app.lbl_statusbar is not None:
            self.app.lbl_statusbar.configure(text="✓ Saved")
            lbl = self.app.lbl_statusbar
            self.app.after(2000, lambda lbl=lbl: lbl.configure(text=f"© {datetime.now().year}  VEN"))

    def _copy_cmd(self):
        teks = " ".join(scrcpy_runner.build_cmd(self.app))
        self.app.clipboard_clear()
        self.app.clipboard_append(teks)
        if self.app.lbl_statusbar is not None:
            self.app.lbl_statusbar.configure(text="✓ Copied!")
            lbl = self.app.lbl_statusbar
            self.app.after(1500, lambda lbl=lbl: lbl.configure(text=f"© {datetime.now().year}  VEN"))

    def _reset_config(self):
        if messagebox.askyesno("Reset", "Reset all settings to default?"):
            try:
                os.remove(CONFIG_FILE)
            except Exception:
                pass
            if self.app.lbl_statusbar is not None:
                self.app.lbl_statusbar.configure(text="Reset — restart to apply")

    def _apply_preset(self, name: str):
        p = PRESETS.get(name)
        if not p:
            return
        self.app.V["bitrate"].set(p["bitrate"])
        self.app.V["fps"].set(p["max_fps"])
        self.app.V["resolution"].set(p["resolution"])
        self.app.V["codec"].set(p["codec"])
        self.app.V["borderless"].set(p["borderless"])
        self.app.V["always_top"].set(p["always_on_top"])
        self.app.V["stay_awake"].set(p["stay_awake"])
        self.app.V["screen_off"].set(p["turn_screen_off"])
        self.app.V["fullscreen"].set(p["fullscreen"])
        self.app.V["no_audio"].set(p["no_audio"])
        self.app.V["view_only"].set(p["no_control"])
        if hasattr(self.app, "_preset_cards"):
            for pname, (card, color) in self.app._preset_cards.items():
                active = pname == name
                card.configure(
                    fg_color=color if active else adb_manager.CARD,
                    border_color=color if active else adb_manager.BDR,
                )
                for w in card.winfo_children():
                    try:
                        w.configure(
                            text_color="white" if active else (
                                color if w.cget("font").cget("size") >= 18 else adb_manager.TEXT
                            )
                        )
                    except Exception:
                        pass
        if self.app.lbl_statusbar is not None:
            self.app.lbl_statusbar.configure(text=f"✓ Preset: {name}")
            lbl = self.app.lbl_statusbar
            self.app.after(2000, lambda lbl=lbl: lbl.configure(text=f"© {datetime.now().year}  VEN"))
