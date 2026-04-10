"""Dependency Checker — startup check, popup, gate popup, update UI."""

import re
import subprocess
import threading

import customtkinter as ctk  # type: ignore

from core.adb_manager import (FN, FNM, check_dependencies, check_optional_dependencies)
import core.adb_manager as adb_manager
from ui.ui_constants import FS

try:
    from PIL import Image  # type: ignore
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

# Semua dependency beserta metadata
_ALL_DEPS = [
    ("scrcpy",  "Android screen cast",    "sudo apt install scrcpy",           True),
    ("adb",     "Android Debug Bridge",   "sudo apt install adb",              True),
    ("ffmpeg",  "Stream encoder",         "sudo apt install ffmpeg",           True),
    ("xdotool", "Window detection",       "sudo apt install xdotool",          True),
    ("pactl",   "PipeWire / PulseAudio",  "sudo apt install pulseaudio-utils", True),
    ("Xvfb",    "Virtual display (live)", "sudo apt install xvfb",             True),
    ("xrandr",  "HiDPI detection",        "sudo apt install x11-xserver-utils",True),
    ("pillow",  "Stream preview canvas",  "pip install pillow",                False),
]

_DEP_VERSION_CMDS = {
    "scrcpy":  (["scrcpy",  "--version"], r"scrcpy\s+([\d.]+)"),
    "ffmpeg":  (["ffmpeg",  "-version"],  r"ffmpeg version ([\S]+)"),
    "adb":     (["adb",     "version"],   r"Android Debug Bridge version ([\d.]+)"),
    "xdotool": (["xdotool", "version"],   r"([\d.]+)"),
    "pactl":   (["pactl",   "--version"], r"pactl ([\S]+)"),
}


# ── Startup check ─────────────────────────────────────────────────────────────

def check_deps_startup(app) -> None:
    """Cek dependency saat startup — tampilkan warning jika ada yang kurang."""
    def _run():
        missing          = check_dependencies()
        optional_missing = check_optional_dependencies()
        if missing:
            app.after(0, lambda: show_dep_warning(app, missing))
        elif optional_missing:
            app.after(0, lambda: show_optional_dep_warning(app, optional_missing))
    threading.Thread(target=_run, daemon=True).start()
    app.after(600, lambda: show_deps_popup(app))


def show_optional_dep_warning(app, missing: list) -> None:
    if "pillow" in missing:
        app.lbl_status.configure(
            text="⚠ Pillow optional missing", text_color=adb_manager.YEL, fg_color=adb_manager.CARD2)


# ── Full deps popup ───────────────────────────────────────────────────────────

def show_deps_popup(app) -> None:
    """Popup lengkap semua dependencies + status + install hint."""
    popup = ctk.CTkToplevel(app)
    popup.title("Dependencies")
    popup.configure(fg_color=adb_manager.BG)
    popup.resizable(False, False)
    popup.attributes("-topmost", True)

    pw, ph = 520, 560
    sx = app.winfo_x() + (app.winfo_width()  - pw) // 2
    sy = app.winfo_y() + (app.winfo_height() - ph) // 2
    popup.geometry(f"{pw}x{ph}+{sx}+{sy}")
    popup.update_idletasks()
    popup.after(100, popup.grab_set)

    # Header
    hdr = ctk.CTkFrame(popup, fg_color=adb_manager.CARD, corner_radius=0, height=46)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    ctk.CTkLabel(hdr, text="📦  Dependencies",
        font=ctk.CTkFont(FN, FS(13), "bold"), text_color=adb_manager.TEXT,
        fg_color="transparent").pack(side="left", padx=16)
    ctk.CTkLabel(hdr, text="Required & optional tools",
        font=ctk.CTkFont(FN, FS(9)), text_color=adb_manager.DIM,
        fg_color="transparent").pack(side="left")

    # Scrollable body
    scroll = ctk.CTkScrollableFrame(popup, fg_color=adb_manager.BG, corner_radius=0)
    scroll.pack(fill="both", expand=True)
    body = ctk.CTkFrame(scroll, fg_color=adb_manager.BG)
    body.pack(fill="both", expand=True, padx=16, pady=(10, 0))

    dot_refs = {}
    for name, desc, install_cmd, required in _ALL_DEPS:
        row = ctk.CTkFrame(body, fg_color=adb_manager.CARD2, corner_radius=8,
                           border_width=1, border_color=adb_manager.BDR)
        row.pack(fill="x", pady=4)

        dot = ctk.CTkLabel(row, text="●",
            font=ctk.CTkFont(FN, FS(12), "bold"),
            text_color=adb_manager.DIM, fg_color="transparent", width=28)
        dot.pack(side="left", padx=(10, 0), pady=8)

        badge       = "required" if required else "optional"
        badge_color = adb_manager.DIM if required else adb_manager.YEL
        ctk.CTkLabel(row, text=name,
            font=ctk.CTkFont(FNM, FS(10), "bold"),
            text_color=adb_manager.ACC, fg_color="transparent",
            width=72, anchor="w").pack(side="left", padx=(6, 0))

        info = ctk.CTkFrame(row, fg_color="transparent")
        info.pack(side="left", fill="x", expand=True, padx=8)
        ctk.CTkLabel(info, text=desc,
            font=ctk.CTkFont(FN, FS(9)), text_color=adb_manager.TEXT,
            fg_color="transparent", anchor="w").pack(anchor="w", pady=(6, 0))
        ctk.CTkLabel(info, text=install_cmd,
            font=ctk.CTkFont(FNM, FS(8)), text_color=adb_manager.ACC,
            fg_color="transparent", anchor="w").pack(anchor="w", pady=(0, 6))

        ctk.CTkLabel(row, text=badge,
            font=ctk.CTkFont(FN, FS(7)), text_color=badge_color,
            fg_color="transparent", width=56, anchor="e").pack(
                side="right", padx=(0, 10))

        dot_refs[name] = dot

    # Tombol bawah
    btn_row = ctk.CTkFrame(popup, fg_color=adb_manager.BG)
    btn_row.pack(fill="x", padx=16, pady=12)

    def _check_all():
        for dot in dot_refs.values():
            dot.configure(text_color=adb_manager.YEL)
        def _run():
            ok_count = 0
            for name, _, _, required in _ALL_DEPS:
                if name == "pillow":
                    ok = _PIL_OK
                else:
                    try:
                        subprocess.run([name, "--version"],
                            capture_output=True, timeout=5)
                        ok = True
                    except FileNotFoundError:
                        ok = False
                    except Exception:
                        ok = True
                if ok: ok_count += 1
                color = adb_manager.GRN if ok else (adb_manager.YEL if not required else adb_manager.RED)
                popup.after(0, lambda d=name, c=color: dot_refs[d].configure(text_color=c))
            total   = len(_ALL_DEPS)
            summary = f"✓ {ok_count}/{total} installed"
            app.after(0, lambda: app._dep_summary_lbl.configure(
                text=summary,
                text_color=adb_manager.GRN if ok_count == total else adb_manager.YEL))
        threading.Thread(target=_run, daemon=True).start()

    ctk.CTkButton(btn_row, text="↺  Check All", command=_check_all,
        height=32, fg_color=adb_manager.ACC, hover_color="#0060cc",
        text_color="white", font=ctk.CTkFont(FN, FS(10), "bold"),
        corner_radius=8).pack(side="left", padx=(0, 8))

    ctk.CTkButton(btn_row, text="Close",
        command=lambda: [popup.grab_release(), popup.destroy()],
        height=32, fg_color=adb_manager.CARD, hover_color=adb_manager.CARD2,
        text_color=adb_manager.DIM, font=ctk.CTkFont(FN, FS(10)),
        border_width=1, border_color=adb_manager.BDR, corner_radius=8).pack(side="right")

    popup.after(300, _check_all)


# ── Version fetch (untuk _dep_rows di Settings tab) ──────────────────────────

def fetch_all_dep_versions(app) -> None:
    """Ambil versi semua dep di background, update UI setelah selesai."""
    def _run():
        results = {}
        for name, (cmd, pattern) in _DEP_VERSION_CMDS.items():
            try:
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                out = r.stdout + r.stderr
                m   = re.search(pattern, out, re.IGNORECASE)
                results[name] = ("ok", m.group(1) if m else "found")
            except FileNotFoundError:
                results[name] = ("missing", "not found")
            except Exception:
                results[name] = ("err", "error")
        app.after(0, lambda: update_dep_ui(app, results))
    threading.Thread(target=_run, daemon=True).start()


def update_dep_ui(app, results: dict) -> None:
    """Update label versi dan dot status di Settings tab."""
    if not hasattr(app, "_dep_rows"):
        return
    for name, (status, ver) in results.items():
        if name not in app._dep_rows:
            continue
        lbl_ver, lbl_status = app._dep_rows[name]
        if status == "ok":
            lbl_ver.configure(text=ver, text_color=adb_manager.DIM)
            lbl_status.configure(text="●", text_color=adb_manager.GRN)
        else:
            lbl_ver.configure(text="not installed", text_color=adb_manager.RED)
            lbl_status.configure(text="●", text_color=adb_manager.RED)
    if hasattr(app, "btn_recheck_deps"):
        app.btn_recheck_deps.configure(state="normal", text="↺ Check")


# ── Warning & gate popup ──────────────────────────────────────────────────────

def show_dep_warning(app, missing: list) -> None:
    """Simpan missing deps dan tampilkan gate popup."""
    app._missing_deps = set(missing)
    app.lbl_status.configure(text="⚠ Missing deps", text_color=adb_manager.YEL, fg_color=adb_manager.CARD2)
    dep_gate_popup(app, missing)


def dep_gate_popup(app, missing: list) -> None:
    """Modal popup — satu baris per dep, tombol re-check dan continue anyway."""
    hints = {
        "scrcpy":  "sudo apt install scrcpy",
        "adb":     "sudo apt install adb",
        "ffmpeg":  "sudo apt install ffmpeg",
        "xdotool": "sudo apt install xdotool",
        "pactl":   "sudo apt install pulseaudio-utils",
        "xvfb":    "sudo apt install xvfb",
    }
    popup = ctk.CTkToplevel(app)
    popup.title("Dependencies Required")
    popup.configure(fg_color=adb_manager.BG)
    popup.resizable(False, False)
    popup.attributes("-topmost", True)
    popup.grab_set()

    popup.update_idletasks()
    pw = 420
    ph = 60 + len(missing) * 52 + 80
    sx = app.winfo_x() + (app.winfo_width()  - pw) // 2
    sy = app.winfo_y() + (app.winfo_height() - ph) // 2
    popup.geometry(f"{pw}x{ph}+{sx}+{sy}")

    # Header
    hdr = ctk.CTkFrame(popup, fg_color=adb_manager.CARD, corner_radius=0, height=48)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    ctk.CTkLabel(hdr, text="⚠  Missing Dependencies",
        font=ctk.CTkFont(FN, FS(13), "bold"), text_color=adb_manager.YEL,
        fg_color="transparent").pack(side="left", padx=16, pady=12)

    ctk.CTkLabel(popup,
        text="These tools must be installed before ScrcpyGUI can work properly.",
        font=ctk.CTkFont(FN, FS(10)), text_color=adb_manager.DIM, fg_color="transparent",
        wraplength=380).pack(pady=(12, 4), padx=16, anchor="w")

    dep_status = {}
    rows_frame = ctk.CTkFrame(popup, fg_color=adb_manager.BG)
    rows_frame.pack(fill="x", padx=16, pady=(4, 0))

    for dep in missing:
        row = ctk.CTkFrame(rows_frame, fg_color=adb_manager.CARD, corner_radius=8,
                           border_width=1, border_color=adb_manager.BDR)
        row.pack(fill="x", pady=4)
        dot = ctk.CTkLabel(row, text="●",
            font=ctk.CTkFont(FN, FS(12), "bold"),
            text_color=adb_manager.RED, fg_color="transparent", width=28)
        dot.pack(side="left", padx=(8, 0))
        ctk.CTkLabel(row, text=dep,
            font=ctk.CTkFont(FNM, FS(10), "bold"),
            text_color=adb_manager.TEXT, fg_color="transparent",
            width=80, anchor="w").pack(side="left", padx=(4, 0))
        ctk.CTkLabel(row, text=hints.get(dep, ""),
            font=ctk.CTkFont(FNM, FS(9)), text_color=adb_manager.DIM,
            fg_color="transparent", anchor="w").pack(
                side="left", padx=8, fill="x", expand=True)
        dep_status[dep] = dot

    btn_row = ctk.CTkFrame(popup, fg_color=adb_manager.BG)
    btn_row.pack(fill="x", padx=16, pady=12)

    def _recheck():
        for dot in dep_status.values():
            dot.configure(text_color=adb_manager.YEL)
        def _do():
            still_missing = []
            for dep in missing:
                cmd = [dep, "version" if dep == "adb" else "--version"]
                try:
                    r  = subprocess.run(cmd, capture_output=True, timeout=5)
                    ok = r.returncode == 0
                except FileNotFoundError:
                    ok = False
                except Exception:
                    ok = True
                popup.after(0, lambda d=dep, o=ok:
                    dep_status[d].configure(text_color=adb_manager.GRN if o else adb_manager.RED))
                if not ok:
                    still_missing.append(dep)
            app._missing_deps = set(still_missing)
            if not still_missing:
                app.after(0, lambda: [
                    app.lbl_status.configure(
                        text="● Ready", text_color=adb_manager.DIM, fg_color=adb_manager.CARD2),
                    btn_continue.configure(
                        state="normal", fg_color=adb_manager.GRN, hover_color="#28a745"),
                    popup.grab_release(),
                ])
        threading.Thread(target=_do, daemon=True).start()

    ctk.CTkButton(btn_row, text="↺  Re-check", command=_recheck,
        height=34, fg_color=adb_manager.CARD2, hover_color=adb_manager.BDR, text_color=adb_manager.DIM,
        font=ctk.CTkFont(FN, FS(10), "bold"),
        border_width=1, border_color=adb_manager.BDR, corner_radius=8).pack(
            side="left", padx=(0, 8))

    btn_continue = ctk.CTkButton(btn_row, text="✓  Continue Anyway",
        command=lambda: [
            setattr(app, "_missing_deps", set()),
            popup.grab_release(),
            popup.destroy()],
        height=34, fg_color=adb_manager.CARD2, hover_color=adb_manager.BDR, text_color=adb_manager.DIM,
        font=ctk.CTkFont(FN, FS(10)),
        border_width=1, border_color=adb_manager.BDR, corner_radius=8)
    btn_continue.pack(side="right")
