"""Live Runner — start/stop livestream via Xvfb + ffmpeg + scrcpy."""

import os
import signal
import subprocess
import threading
import time
from datetime import datetime
from tkinter import messagebox

from core.adb_manager import (PLATFORM_RTMP, COMPOSITOR_FIXES, detect_compositor, detect_audio_monitor)
import core.adb_manager as adb_manager
from ui import preview_manager, scrcpy_runner


# ── Start Livestream ──────────────────────────────────────────────────────────

def start_live(app) -> None:
    """Validasi input, jalankan Xvfb + scrcpy, lalu mulai ffmpeg streaming."""
    dev = app.V["device"].get()
    if not dev or "no devices" in dev:
        messagebox.showwarning("No Device", "Select a device first!"); return

    key = app.V["live_key"].get().strip()
    if not key:
        messagebox.showwarning("Missing Stream Key", "Enter Stream Key first!"); return

    plat = app.V["live_platform"].get()
    base = PLATFORM_RTMP.get(plat, "")

    if plat == "Custom":
        custom_url = app.V["live_custom_url"].get().strip()
        if not custom_url:
            messagebox.showwarning("Missing RTMP URL", "Enter Custom RTMP URL first!"); return
        rtmp_url = custom_url.rstrip("/") + "/" + key if key else custom_url
    else:
        rtmp_url = base + key

    # ── Xvfb: scrcpy jalan di virtual display ────────────────────────────────
    live_res = app.V["live_res"].get() or "1280x720"
    xvfb_cmd = ["Xvfb", app.xvfb_display, "-screen", "0", f"{live_res}x24"]
    app._log(f"$ {' '.join(xvfb_cmd)}")
    try:
        app.xvfb_proc = subprocess.Popen(
            xvfb_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.6)
        app._log(f"→ Xvfb started on {app.xvfb_display} ({live_res})")
    except FileNotFoundError:
        messagebox.showerror("Error", "Xvfb not found!\nsudo apt install xvfb"); return
    except Exception as e:
        messagebox.showerror("Error", f"Xvfb failed: {e}"); return

    # ── scrcpy di virtual display ─────────────────────────────────────────────
    # For livestream, run scrcpy fullscreen on the virtual display so the
    # capture region fills the screen and avoids extra black margins.
    scrcpy_cmd = scrcpy_runner.build_cmd(app, force_always_on_top=True)
    scrcpy_env = {**os.environ, "DISPLAY": app.xvfb_display}
    _comp = detect_compositor()
    if _comp and _comp in COMPOSITOR_FIXES:
        scrcpy_env.update(COMPOSITOR_FIXES[_comp][1])

    app._log(f"$ DISPLAY={app.xvfb_display} {' '.join(scrcpy_cmd)}")
    try:
        app.process = subprocess.Popen(
            scrcpy_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            env=scrcpy_env)
        app.running      = True
        app.live_running = True
        ui_set_running(app, label="■   Stop Live", color=adb_manager.RED)
        app._log("→ Waiting for scrcpy on virtual display...")
        threading.Thread(
            target=lambda: _wait_window_then_stream(app, rtmp_url, plat),
            daemon=True).start()
        threading.Thread(
            target=lambda: _wait_process(app),
            daemon=True).start()
        preview_manager.start_elapsed_timer(app)
        if app.V["preview_auto_start"].get():
            app.after(3000, lambda: preview_manager.start_preview_loop(app, manual=False))
    except FileNotFoundError:
        messagebox.showerror("Error", "scrcpy not found!")
    except Exception as e:
        messagebox.showerror("Error", str(e))


# ── Wait for scrcpy window → launch ffmpeg ────────────────────────────────────

def _wait_window_then_stream(app, rtmp_url: str, plat: str) -> None:
    """Tunggu scrcpy muncul di virtual display, lalu jalankan ffmpeg."""
    xenv   = {**os.environ, "DISPLAY": app.xvfb_display}
    win_id = None

    for _ in range(20):
        try:
            r = subprocess.run(
                ["xdotool", "search", "--class", "scrcpy"],
                capture_output=True, text=True, timeout=2, env=xenv)
            if r.returncode == 0 and r.stdout.strip():
                win_id = r.stdout.strip().splitlines()[0]; break
        except FileNotFoundError:
            app._log("ERROR: xdotool not found!"); return
        except Exception:
            pass
        time.sleep(0.5)

    if not win_id:
        app._log("ERROR: scrcpy not found on virtual display"); return

    live_res = app.V["live_res"].get() or "1280x720"
    try:
        rw, rh = live_res.split("x")
        rw = int(rw) - (int(rw) % 2)
        rh = int(rh) - (int(rh) % 2)
    except Exception:
        rw, rh = 1280, 720

    br      = app.V["live_bitrate"].get()
    fps     = app.V["live_fps"].get()
    bufsize = str(int(br.replace("k", "")) * 2) + "k"
    gop     = str(int(fps))
    monitor = detect_audio_monitor()

    mic_args = (
        ["-thread_queue_size", "4096", "-f", "pulse", "-ac", "2", "-i", "default",
         "-filter_complex", "amix=inputs=2:duration=first:dropout_transition=0"]
        if app.V["live_mic"].get() else []
    )

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "x11grab", "-draw_mouse", "0",
        "-framerate", fps, "-r", fps,
        "-s", f"{rw}x{rh}", "-i", f"{app.xvfb_display}.0+0,0",
        "-thread_queue_size", "4096", "-f", "pulse", "-ac", "2", "-i", monitor,
        *mic_args,
        "-threads", "2",
        "-c:v", "libx264", "-preset", "superfast", "-tune", "zerolatency",
        "-b:v", br, "-maxrate", br, "-bufsize", bufsize,
        "-pix_fmt", "yuv420p", "-g", gop,
        "-af", "aresample=48000:resampler=soxr",
        "-c:a", "aac", "-b:a", "128k", "-ar", "48000",
        "-f", "flv", rtmp_url,
    ]
    app._log(f"$ {' '.join(ffmpeg_cmd)}")
    try:
        app.ffmpeg_proc = subprocess.Popen(
            ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        threading.Thread(target=lambda: _read_ffmpeg_log(app), daemon=True).start()
        threading.Thread(target=lambda: _wait_ffmpeg_proc(app), daemon=True).start()
        app._log(f"→ Live started to {plat}! 🔴  [{rw}×{rh}] virtual display")
        app.tabview.set("🔴  Livestream")
    except Exception as e:
        app._log(f"ERROR ffmpeg: {e}")


def _read_ffmpeg_log(app) -> None:
    if not app.ffmpeg_proc or not app.ffmpeg_proc.stderr:
        return
    for baris in app.ffmpeg_proc.stderr:
        baris = baris.decode(errors="replace").rstrip()
        if any(k in baris.lower() for k in ["fps=", "bitrate=", "error", "failed", "speed="]):
            app._log(f"[ffmpeg] {baris}")


def _wait_ffmpeg_proc(app) -> None:
    if app.ffmpeg_proc:
        app.ffmpeg_proc.wait()
    if app.live_running:
        app._log("→ ffmpeg stopped")
        app.after(0, lambda: sudah_stop(app))


# ── UI running state ──────────────────────────────────────────────────────────

def ui_set_running(app, label="■   Stop", color=adb_manager.RED) -> None:
    """Update semua tombol dan label ke state 'sedang berjalan'."""
    app.btn_start.configure(text=label, fg_color=color, hover_color="#cc0000")
    mode = app.V["mode"].get()
    if mode == "Livestream" and hasattr(app, "btn_start_live"):
        app.btn_start_live.configure(
            text="■   Stop Livestream", fg_color=adb_manager.RED, hover_color="#cc0000")
    pid = app.process.pid if app.process else "?"
    st  = f"🔴 LIVE  pid:{pid}" if mode == "Livestream" else f"● {mode}  pid:{pid}"
    app.lbl_status.configure(
        text=st,
        text_color=adb_manager.RED if mode == "Livestream" else adb_manager.GRN,
        fg_color=adb_manager.CARD2)
    app.lbl_statusbar.configure(text=st)
    app.float_btn_toggle.configure(text="■", text_color=adb_manager.RED)
    if mode == "Livestream":
        app._float_live_mode(True)


# ── Stop ──────────────────────────────────────────────────────────────────────

def _read_output(app) -> None:
    if app.process and app.process.stdout:
        for brs in app.process.stdout:
            app._log(brs.rstrip())


def _wait_process(app) -> None:
    if app.process:
        app.process.wait()
    app.after(0, lambda: sudah_stop(app))


def stop(app) -> None:
    """Hentikan semua proses: ffmpeg, scrcpy, Xvfb, dan semua device."""
    for proc in [app.ffmpeg_proc, app.process, app.xvfb_proc]:
        if proc:
            try: proc.terminate()
            except Exception: pass

    for proc in app.processes.values():
        try: proc.terminate()
        except Exception: pass

    app.processes.clear()
    app.running_devs.clear()
    kill_orphans(app)
    app.after(100, lambda: device_manager_refresh(app))
    sudah_stop(app)
    scrcpy_runner.update_header_status(app)


def kill_orphans(app) -> None:
    """Kill proses ffmpeg/Xvfb sisa dari sesi ini."""
    try:
        r = subprocess.run(
            ["ps", "-u", os.environ.get("USER", ""), "-o", "pid,args", "--no-headers"],
            capture_output=True, text=True, timeout=5)
        for line in r.stdout.splitlines():
            line     = line.strip()
            pid_str  = line.split()[0] if line else ""
            if not pid_str.isdigit(): continue
            pid = int(pid_str)
            if pid == os.getpid(): continue
            if "ffmpeg" in line and "rtmp://" in line:
                try: os.kill(pid, signal.SIGTERM)
                except Exception: pass
            elif f"Xvfb {app.xvfb_display}" in line:
                try: os.kill(pid, signal.SIGTERM)
                except Exception: pass
    except Exception:
        pass


def sudah_stop(app) -> None:
    """Reset semua state dan UI ke kondisi idle."""
    app.running = app.live_running = False
    app.process = app.ffmpeg_proc = app.xvfb_proc = None

    mode  = app.V["mode"].get()
    label = "▶  Start Live" if mode == "Livestream" else "▶  Start"
    try:
        app.btn_start.configure(text=label, fg_color=adb_manager.ACC, hover_color="#0060cc")
    except Exception:
        pass

    if mode == "Livestream" and hasattr(app, "btn_start_live"):
        app.btn_start_live.configure(
            text="🔴  Start Livestream", fg_color=adb_manager.RED, hover_color="#cc0000")

    app.lbl_status.configure(text="● Ready", text_color=adb_manager.DIM, fg_color=adb_manager.CARD2)
    app.lbl_statusbar.configure(text=f"© {datetime.now().year}  VEN")
    app._log("→ stopped\n")
    app.float_btn_toggle.configure(text="▶", text_color=adb_manager.GRN)
    app._float_live_mode(False)
    preview_manager.stop_preview_loop(app)

    if hasattr(app, "btn_start_all"):
        connected = len(app._all_devices)
        app.btn_start_all.configure(
            text="▶▶  All",
            command=lambda: scrcpy_runner.start_all(app),
            fg_color=adb_manager.GRN   if connected > 1 else adb_manager.CARD2,
            hover_color="#28a745" if connected > 1 else adb_manager.CARD2,
            state="normal" if connected > 1 else "disabled")


def device_manager_refresh(app) -> None:
    """Proxy ke device_manager.refresh_devices — hindari circular import."""
    from ui import device_manager
    device_manager.refresh_devices(app)
