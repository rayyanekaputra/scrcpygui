"""Scrcpy Runner — build command, start/stop/toggle device mirroring."""

import os
import subprocess
import threading
import time
from datetime import datetime
from tkinter import messagebox

from core.adb_manager import (FN, COMPOSITOR_FIXES, detect_compositor)
import core.adb_manager as adb_manager
from ui import device_manager


# ── Build command ─────────────────────────────────────────────────────────────

def build_cmd_for(app, serial="", idx=0, total=1, force_always_on_top=False) -> list:
    """Bangun list argumen scrcpy berdasarkan semua setting saat ini."""
    mode = app.V["mode"].get()
    cmd  = ["scrcpy"]
    if serial:
        cmd += ["-s", serial]

    _comp = detect_compositor()
    if _comp and _comp in COMPOSITOR_FIXES:
        cmd += COMPOSITOR_FIXES[_comp][0]

    cmd += ["--video-bit-rate", app.V["bitrate"].get()]
    cmd += ["--max-fps",        app.V["fps"].get()]

    res = app.V["resolution"].get()
    if res and res != "(default)":
        cmd += ["--max-size", res]

    if app.V["codec"].get() != "h264":
        cmd += ["--video-codec", app.V["codec"].get()]

    enc_label = app.V["video_encoder"].get()
    enc_raw   = device_manager.ENCODER_LABEL_MAP.get(enc_label, enc_label)
    if enc_raw and enc_raw != "(auto)":
        cmd += ["--video-encoder", enc_raw]

    if app.V["rotation"].get() != "0":
        cmd += ["--display-orientation", app.V["rotation"].get()]

    if mode == "Record":
        path = app.V["rec_path"].get()
        fmt  = app.V["rec_fmt"].get() or "mp4"
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs(path, exist_ok=True)
        cmd += ["--record", os.path.join(path, f"rec_{serial}_{ts}.{fmt}")]

    if app.V["no_audio"].get():
        cmd += ["--no-audio"]

    if force_always_on_top:
        cmd += ["--always-on-top", "--fullscreen"]
    elif total > 1:
        x, y, w, h = calc_tile(app, idx, total)
        cmd += ["--window-x", str(x), "--window-y", str(y),
                "--window-width", str(w), "--window-height", str(h)]
        title = app.V["win_title"].get() or "scrcpy"
        cmd += ["--window-title", f"{title} [{serial}]"]
    else:
        if app.V["fullscreen"].get():   cmd += ["--fullscreen"]
        if app.V["borderless"].get():   cmd += ["--window-borderless"]
        if app.V["always_top"].get():   cmd += ["--always-on-top"]
        title = app.V["win_title"].get()
        if title and title != "scrcpy": cmd += ["--window-title", title]

    if app.V["stay_awake"].get() and not app.V["view_only"].get():
        cmd += ["--stay-awake"]
    if app.V["screen_off"].get(): cmd += ["--turn-screen-off"]
    if app.V["view_only"].get():  cmd += ["--no-control"]

    return cmd


def build_cmd(app, force_always_on_top=False) -> list:
    """Versi singkat — pakai device yang sedang dipilih."""
    dev = app.V["device"].get()
    serial = dev.split()[0] if dev and "no devices" not in dev else ""
    return build_cmd_for(app, serial, 0, 1, force_always_on_top)


# ── Toggle / Start / Stop ─────────────────────────────────────────────────────

def toggle(app) -> None:
    """Tombol utama Start/Stop — routing ke live atau mirror."""
    if app.live_running:
        app._stop(); return
    if len(app.running_devs) > 1:
        stop_all(app); return

    dev = app.V["device"].get()
    if not dev or "no devices" in dev:
        messagebox.showwarning("No Device", "Select a device first!")
        return

    serial = serial_from_label(app, dev)
    if not serial:
        return

    if app.V["mode"].get() == "Livestream":
        missing   = getattr(app, "_missing_deps", set())
        live_deps = missing & {"ffmpeg", "xdotool", "pactl", "scrcpy"}
        if live_deps:
            app._dep_gate_popup(list(live_deps)); return
        app.V["device"].set(dev)
        app._start_live()
    else:
        toggle_device(app, serial)


def start_all(app) -> None:
    """Mulai mirroring semua device yang tersedia secara tiled."""
    if not app._all_devices:
        messagebox.showwarning("No Devices", "No devices found!"); return
    total = len(app._all_devices)
    for idx, (serial, _) in enumerate(app._all_devices):
        if serial not in app.running_devs:
            start_device_tiled(app, serial, idx, total)
    app.btn_start_all.configure(
        text="■  Stop All", command=lambda: stop_all(app),
        fg_color=adb_manager.RED, hover_color="#cc0000", state="normal")


def stop_all(app) -> None:
    """Hentikan semua device yang sedang berjalan."""
    for serial in list(app.running_devs):
        stop_device(app, serial)
    app.btn_start_all.configure(
        text="▶▶  All", command=lambda: start_all(app),
        fg_color=adb_manager.GRN, hover_color="#28a745")


def serial_from_label(app, label: str) -> str:
    """Cari serial dari label combo device."""
    for serial, lbl in app._all_devices:
        if lbl == label:
            return serial
    return label.split()[0] if label else ""


# ── Per-device start/stop ─────────────────────────────────────────────────────

def start_device_tiled(app, serial: str, idx: int, total: int,
                       _retry_encoder: str = "") -> None:
    """Jalankan scrcpy untuk satu device dengan posisi tiled."""
    cmd = build_cmd_for(app, serial, idx, total)
    if _retry_encoder:
        cmd += ["--video-encoder", _retry_encoder]
        label = device_manager.encoder_label(_retry_encoder)
        app._log(f"→ Retrying with: {label} ({_retry_encoder})")

    app._log(f"\n$ {' '.join(cmd)}")
    try:
        _comp     = detect_compositor()
        _comp_env = COMPOSITOR_FIXES[_comp][1] if (_comp and _comp in COMPOSITOR_FIXES) else {}
        proc_env  = {**os.environ, **_comp_env} if _comp_env else None

        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, env=proc_env)

        app.processes[serial] = proc
        app.running_devs.add(serial)
        app._proc_start_times = getattr(app, "_proc_start_times", {})
        app._proc_start_times[serial] = time.time()
        update_header_status(app)

        if len(app.running_devs) > 1:
            app.V["fullscreen"].set(False)
            app.V["borderless"].set(False)

        threading.Thread(
            target=lambda: _wait_device_process(app, serial, proc, _retry_encoder),
            daemon=True).start()

    except FileNotFoundError:
        messagebox.showerror("Error", "scrcpy not found!")
    except Exception as e:
        messagebox.showerror("Error", str(e))


def toggle_device(app, serial: str) -> None:
    """Toggle satu device: start jika idle, stop jika berjalan."""
    if serial in app.running_devs:
        stop_device(app, serial)
    else:
        start_device_tiled(app, serial, len(app.running_devs),
                           max(len(app.running_devs) + 1, 1))


def calc_tile(app, idx: int, total: int) -> tuple:
    """Hitung posisi dan ukuran window untuk layout tiled."""
    sw = app.winfo_screenwidth()
    sh = app.winfo_screenheight() - 80
    if total == 1:   return sw // 4, 40, sw // 2, int(sh * 0.8)
    elif total == 2: return idx * (sw // 2), 40, sw // 2, sh
    elif total == 3: return idx * (sw // 3), 40, sw // 3, sh
    elif total == 4: return (idx % 2) * (sw // 2), 40 + (idx // 2) * (sh // 2), sw // 2, sh // 2
    else:            return (idx % 3) * (sw // 3), 40 + (idx // 3) * (sh // 2), sw // 3, sh // 2


def stop_device(app, serial: str) -> None:
    """Hentikan proses scrcpy untuk satu device."""
    proc = app.processes.pop(serial, None)
    if proc:
        try: proc.terminate()
        except Exception: pass
    app.running_devs.discard(serial)
    update_header_status(app)
    app._log(f"→ Stopped: {serial}\n")


# ── Header status ─────────────────────────────────────────────────────────────

def update_header_status(app) -> None:
    """Update label status, tombol start, dan floating button."""
    n               = len(app.running_devs)
    dev             = app.V["device"].get()
    sel_serial      = serial_from_label(app, dev) if dev and "no devices" not in dev else ""
    sel_running     = sel_serial in app.running_devs

    if n == 0:
        app.lbl_status.configure(text="● Ready", text_color=adb_manager.DIM, fg_color=adb_manager.CARD2)
        app.lbl_statusbar.configure(text=f"© {datetime.now().year}  VEN")
        app.btn_start.configure(text="▶  Start", fg_color=adb_manager.ACC, hover_color="#0060cc")
        app.float_btn_toggle.configure(text="▶", text_color=adb_manager.GRN)
        app.running = False
        if hasattr(app, "btn_start_all"):
            connected = len(app._all_devices)
            app.btn_start_all.configure(
                text="▶▶  All", command=lambda: start_all(app),
                fg_color=adb_manager.GRN  if connected > 1 else adb_manager.CARD2,
                hover_color="#28a745" if connected > 1 else adb_manager.CARD2,
                state="normal" if connected > 1 else "disabled")
    else:
        app.lbl_status.configure(
            text=f"● Mirroring  {n} device(s)", text_color=adb_manager.GRN, fg_color=adb_manager.CARD2)
        app.lbl_statusbar.configure(text=f"● {n} device(s) active")
        app.running = True
        if sel_running:
            app.btn_start.configure(text="■  Stop", fg_color=adb_manager.RED, hover_color="#cc0000")
        else:
            app.btn_start.configure(text="▶  Start", fg_color=adb_manager.ACC, hover_color="#0060cc")
        app.float_btn_toggle.configure(text="■", text_color=adb_manager.RED)


# ── Process monitoring ────────────────────────────────────────────────────────

def _wait_device_process(app, serial: str, proc, _used_encoder: str = "") -> None:
    """Monitor proses scrcpy — deteksi crash MediaCodec dan auto-retry."""
    start        = getattr(app, "_proc_start_times", {}).get(serial, time.time())
    output_lines = []
    try:
        for line in proc.stdout:
            output_lines.append(line.rstrip())
    except Exception:
        pass
    proc.wait()

    elapsed     = time.time() - start
    full_output = "\n".join(output_lines)
    for ln in output_lines:
        app._log(f"[{serial}] {ln}")

    is_codec_err = "MediaCodec" in full_output or "CodecException" in full_output
    if elapsed < 8 and is_codec_err and not _used_encoder:
        app._log("⚠ MediaCodec error detected — retrying with OMX.google.h264.encoder…")
        app.after(0, lambda: codec_fallback(app, serial))
    else:
        app.after(0, lambda: on_device_stopped(app, serial))


def codec_fallback(app, serial: str) -> None:
    """Auto-retry dengan software encoder setelah MediaCodec crash."""
    app.processes.pop(serial, None)
    app.running_devs.discard(serial)

    fallback_raw   = "OMX.google.h264.encoder"
    fallback_label = device_manager.encoder_label(fallback_raw)

    if hasattr(app, "combo_encoder"):
        if fallback_label not in device_manager.ENCODER_LABEL_MAP:
            device_manager.ENCODER_LABEL_MAP[fallback_label] = fallback_raw
            vals = list(app.combo_encoder.cget("values"))
            if fallback_label not in vals:
                vals.insert(1, fallback_label)
                app.combo_encoder.configure(values=vals)
        app.V["video_encoder"].set(fallback_label)

    idx   = len(app.running_devs)
    total = max(len(app._all_devices), 1)
    start_device_tiled(app, serial, idx, total, _retry_encoder=fallback_raw)


def on_device_stopped(app, serial: str) -> None:
    """Cleanup setelah proses scrcpy berhenti sendiri."""
    if serial in app.running_devs:
        app.processes.pop(serial, None)
        app.running_devs.discard(serial)
        update_header_status(app)
        app._log(f"→ {serial} disconnected\n")
