"""Preview Manager — stream preview canvas, capture loop, dan elapsed timer."""

import math
import os
import subprocess
import threading
import time

from core.adb_manager import (FN, FNM, PLATFORM_RTMP, detect_audio_monitor, capture_device_preview)
import core.adb_manager as adb_manager
from ui.ui_constants import FS

PREVIEW_TMP = "/tmp/scrcpygui_preview.png"
_PREV_W, _PREV_H = 316, 178

try:
    from PIL import Image, ImageTk  # type: ignore
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

try:
    import tkinter as tk
except ImportError:
    tk = None  # type: ignore


# ── Command preview (txt_cmd / txt_cmd_live) ──────────────────────────────────

def update_cmd_preview(app) -> None:
    """Update text widget preview command berdasarkan mode aktif."""
    try:
        mode = app.V["mode"].get()
        if mode == "Livestream":
            plat   = app.V["live_platform"].get()
            base   = PLATFORM_RTMP.get(plat, "")
            rtmp   = base + "<KEY>" if base else "<RTMP_URL>"
            br     = app.V["live_bitrate"].get()
            fps    = app.V["live_fps"].get()
            mic    = app.V["live_mic"].get()
            monitor = detect_audio_monitor()
            mic_part = (
                " \\\n  -f pulse -i default \\\n  -filter_complex amix=inputs=2"
                if mic else ""
            )
            teks = (
                f"# scrcpy\n{' '.join(app._build_cmd(force_always_on_top=True))}\n\n"
                f"# ffmpeg\nffmpeg -f x11grab -draw_mouse 0 \\\n"
                f"  -framerate {fps} -r {fps} -s <screen_res> -i :0.0+0,0 \\\n"
                f"  -f pulse -i {monitor}{mic_part} \\\n"
                f"  -c:v libx264 -preset superfast -b:v {br} \\\n"
                f"  -pix_fmt yuv420p -g {fps} \\\n"
                f"  -c:a aac -b:a 128k -f flv {rtmp}"
            )
            _upd(app, app.txt_cmd_live, teks)
        _upd(app, app.txt_cmd, " ".join(app._build_cmd()))
    except Exception:
        pass


def _upd(app, w, t) -> None:
    """Update isi CTkTextbox (state-safe)."""
    w.configure(state="normal")
    w.delete("0.0", "end")
    w.insert("0.0", t)
    w.configure(state="disabled")


# ── Canvas helpers ────────────────────────────────────────────────────────────

def preview_placeholder(app) -> None:
    """Gambar idle placeholder di canvas."""
    c = app.preview_canvas
    c.delete("all")
    W, H = _PREV_W, _PREV_H
    c.create_rectangle(0, 0, W, H, fill="#111111", outline="")
    for x in range(0, W, 32):
        c.create_line(x, 0, x, H, fill="#1a1a1a", width=1)
    for y in range(0, H, 32):
        c.create_line(0, y, W, y, fill="#1a1a1a", width=1)
    c.create_text(W // 2, H // 2 - 18, text="📱", font=(FN, 28), fill="#333333")
    c.create_text(W // 2, H // 2 + 18, text="No Preview",
                  font=(FNM, 10), fill="#444444")
    c.create_text(W // 2, H // 2 + 36, text="press Capture or start streaming",
                  font=(FN, 8), fill="#333333")


def canvas_message(app, msg: str, color: str = "#666666") -> None:
    """Tampilkan pesan terpusat di canvas."""
    c = app.preview_canvas
    c.delete("all")
    W, H = _PREV_W, _PREV_H
    c.create_rectangle(0, 0, W, H, fill="#111111", outline="")
    c.create_text(W // 2, H // 2, text=msg, font=(FN, 10),
                  fill=color, justify="center")


# ── Capture loop ──────────────────────────────────────────────────────────────

def toggle_preview(app) -> None:
    """Tombol Capture/Stop handler."""
    if app._preview_active:
        stop_preview_loop(app)
    else:
        start_preview_loop(app, manual=True)


def start_preview_loop(app, manual: bool = False) -> None:
    """Mulai periodic preview capture."""
    app._preview_active = True
    if manual:
        app.btn_preview_toggle.configure(
            text="■  Stop", fg_color=adb_manager.RED, hover_color="#cc0000",
            text_color="white", border_width=0)
        app.lbl_preview_status.configure(text="capturing…", text_color=adb_manager.YEL)
    _schedule_capture(app)


def stop_preview_loop(app) -> None:
    """Hentikan capture dan reset canvas."""
    app._preview_active = False
    try:
        app.btn_preview_toggle.configure(
            text="📷  Capture", fg_color=adb_manager.CARD2, hover_color=adb_manager.BDR,
            text_color=adb_manager.DIM, border_width=1, border_color=adb_manager.BDR)
        app.lbl_preview_status.configure(text="idle", text_color=adb_manager.DIM)
        app.lbl_preview_res.configure(text="")
        if not app.live_running:
            app.lbl_preview_time.configure(text="--:--:--")
        preview_placeholder(app)
    except Exception:
        pass


def _schedule_capture(app) -> None:
    """Jadwalkan satu frame capture jika masih aktif."""
    if not app._preview_active or getattr(app, "_preview_capture_running", False):
        return
    app._preview_capture_running = True
    threading.Thread(target=lambda: _do_capture(app), daemon=True).start()


def _do_capture(app) -> None:
    """Capture satu frame — X11 saat live, ADB saat idle."""
    try:
        if app.live_running:
            _capture_x11(app)
        else:
            _capture_adb(app)
    except subprocess.TimeoutExpired:
        app.after(0, lambda: canvas_message(app, "Capture timeout", adb_manager.YEL))
    except Exception as e:
        app.after(0, lambda err=e: canvas_message(app, f"Error:\n{err}", adb_manager.RED))
    finally:
        app._preview_capture_running = False

    if app._preview_active:
        try:
            ms = int(app.V["preview_interval"].get().replace("s", "")) * 1000
        except Exception:
            ms = 2000
        app.after(ms, lambda: _schedule_capture(app))


def _capture_x11(app) -> None:
    """Grab frame dari Xvfb virtual display."""
    live_res = app.V["live_res"].get() or "1280x720"
    try:
        rw, rh = live_res.split("x")
        rw = int(rw) - (int(rw) % 2)
        rh = int(rh) - (int(rh) % 2)
    except Exception:
        rw, rh = 1280, 720

    xvfb_env = {**os.environ, "DISPLAY": app.xvfb_display}
    cmd = [
        "ffmpeg", "-y",
        "-f", "x11grab", "-framerate", "1",
        "-s", f"{rw}x{rh}", "-i", f"{app.xvfb_display}+0,0",
        "-vframes", "1", "-vf", "scale=316:-2",
        PREVIEW_TMP,
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=10, env=xvfb_env)
    if r.returncode == 0 and os.path.exists(PREVIEW_TMP):
        app.after(0, lambda: update_preview_canvas(app, PREVIEW_TMP, source="x11"))
    else:
        err = r.stderr.decode(errors="replace").strip().splitlines()
        last = err[-1] if err else "unknown error"
        app.after(0, lambda e=last: canvas_message(app, "Grab failed: " + e, adb_manager.RED))


def _capture_adb(app) -> None:
    """Grab screenshot dari device via ADB."""
    dev = app.V["device"].get()
    if not dev or "no devices" in dev:
        app.after(0, lambda: canvas_message(app, "No device\nconnected"))
        app._preview_active = False
        app.after(0, lambda: stop_preview_loop(app))
        return

    serial = dev.split()[0]
    r = subprocess.run(
        ["adb", "-s", serial, "exec-out", "screencap", "-p"],
        capture_output=True, timeout=12)

    if r.returncode == 0 and r.stdout:
        with open(PREVIEW_TMP, "wb") as f:
            f.write(r.stdout)
        app.after(0, lambda: update_preview_canvas(app, PREVIEW_TMP, source="adb"))
    else:
        ok, _ = capture_device_preview(serial, PREVIEW_TMP)
        if ok:
            app.after(0, lambda: update_preview_canvas(app, PREVIEW_TMP, source="adb"))
        else:
            app.after(0, lambda: canvas_message(app, "ADB screenshot\nfailed", adb_manager.RED))


def update_preview_canvas(app, path: str, source: str = "adb") -> None:
    """Load gambar dari path dan render ke preview_canvas."""
    if not os.path.exists(path):
        return
    CW, CH = _PREV_W, _PREV_H
    try:
        c = app.preview_canvas
        c.delete("all")
        c.create_rectangle(0, 0, CW, CH, fill="#000000", outline="")

        if _PIL_OK:
            img = Image.open(path).convert("RGB")
            img.thumbnail((CW, CH), Image.LANCZOS)  # type: ignore
            iw, ih = img.size
            photo = ImageTk.PhotoImage(img)
        else:
            photo = tk.PhotoImage(file=path)
            iw, ih = photo.width(), photo.height()
            if iw > CW or ih > CH:
                scale = max(iw / CW, ih / CH)
                subsample = max(1, math.ceil(scale))
                photo = photo.subsample(subsample, subsample)  # type: ignore
                iw, ih = photo.width(), photo.height()

        app._preview_img_ref = photo  # cegah GC
        c.create_image((CW - iw) // 2, (CH - ih) // 2, anchor="nw", image=photo)

        # Badge sumber (kiri atas)
        badge_text  = "🔴 LIVE" if source == "x11" else "📱 ADB"
        badge_color = adb_manager.RED if source == "x11" else adb_manager.ACC
        c.create_rectangle(4, 4, 72, 18, fill="#000000", stipple="gray50", outline="")
        c.create_text(38, 11, text=badge_text, font=(FNM, 7, "bold"),
                      fill=badge_color, anchor="center")

        app.lbl_preview_res.configure(text=f"{iw}×{ih}")
        app.lbl_preview_status.configure(
            text="live" if source == "x11" else "adb",
            text_color=adb_manager.RED if source == "x11" else adb_manager.ACC)
    except Exception as e:
        canvas_message(app, f"Load error:\n{e}", adb_manager.RED)


# ── Elapsed timer ─────────────────────────────────────────────────────────────

def start_elapsed_timer(app) -> None:
    """Mulai elapsed timer saat live dimulai."""
    app._preview_start_time = time.time()
    _tick_elapsed(app)


def _tick_elapsed(app) -> None:
    """Update label elapsed time setiap detik selama live berjalan."""
    if not app.live_running:
        try:
            app.lbl_preview_time.configure(text="--:--:--", text_color=adb_manager.DIM)
        except Exception:
            pass
        return
    if app._preview_start_time:
        elapsed = int(time.time() - app._preview_start_time)
        h = elapsed // 3600
        m = (elapsed % 3600) // 60
        s = elapsed % 60
        try:
            app.lbl_preview_time.configure(
                text=f"{h:02d}:{m:02d}:{s:02d}", text_color=adb_manager.RED)
        except Exception:
            pass
    app.after(1000, lambda: _tick_elapsed(app))
