"""Device Manager — scan ADB, encoder detection, device combo update."""

import subprocess
import threading

from core.adb_manager import FN, scan_devices
import core.adb_manager as adb_manager

# Module-level encoder label map: {"H.264 Software (Google)": "OMX.google.h264.encoder"}
# Sebelumnya App._ENCODER_LABEL_MAP — dipindah ke sini agar tidak bergantung ke class.
ENCODER_LABEL_MAP: dict = {}


# ── Refresh & scan ────────────────────────────────────────────────────────────

def refresh_devices(app) -> None:
    """Trigger scan ADB di background thread."""
    app.lbl_device_info.configure(text="Scanning...", text_color=adb_manager.DIM)
    app._log("$ adb devices -l")
    threading.Thread(target=lambda: _scan_adb(app), daemon=True).start()


def _scan_adb(app) -> None:
    devices, log = scan_devices()
    app.after(0, lambda: set_devices(app, devices, log))


def set_devices(app, devices, log) -> None:
    """Update combo device dan info label setelah scan selesai."""
    app._log(log)
    app.dev_rows = {}
    app._all_devices = devices

    if not devices:
        app.combo_device.configure(values=["(no devices)"])
        app.V["device"].set("(no devices)")
        app.lbl_device_info.configure(
            text="Connect a device and enable USB Debugging", text_color=adb_manager.YEL)
        return

    labels = [label for _, label in devices]
    app.combo_device.configure(values=labels)
    app.V["device"].set(labels[0])

    count = len(devices)
    info  = f"✓ {count} device(s)"
    if count > 1:
        info += "  —  Use Start All to mirror all devices"
    app.lbl_device_info.configure(text=info, text_color=adb_manager.GRN)
    update_start_all_btn(app, count)

    # Auto-fetch encoder dari device pertama
    first_serial = devices[0][0]
    if hasattr(app, "lbl_encoder_hint"):
        app.lbl_encoder_hint.configure(text="detecting…")
    fetch_encoders(app, first_serial)


# ── Device selected ───────────────────────────────────────────────────────────

def on_device_selected(app, label: str) -> None:
    """Dipanggil saat user ganti device di combo — fetch encoder baru."""
    serial = app._serial_from_label(label)
    if serial and "no devices" not in serial:
        if hasattr(app, "lbl_encoder_hint"):
            app.lbl_encoder_hint.configure(text="detecting…")
        fetch_encoders(app, serial)


# ── Encoder detection ─────────────────────────────────────────────────────────

def encoder_label(raw: str) -> str:
    """Ubah nama encoder teknis jadi label yang mudah dibaca."""
    raw_l = raw.lower()
    # Vendor
    if "google" in raw_l:
        vendor = "Google"
    elif "qcom" in raw_l or "qualcomm" in raw_l:
        vendor = "Qualcomm"
    elif "mtk" in raw_l or "mediatek" in raw_l:
        vendor = "MediaTek"
    elif "exynos" in raw_l or "samsung" in raw_l:
        vendor = "Samsung"
    elif "c2.android" in raw_l:
        vendor = "Android"
    else:
        vendor = raw.split(".")[1].capitalize() if raw.count(".") >= 2 else "HW"
    # Codec
    if "h264" in raw_l or "avc" in raw_l:
        codec = "H.264"
    elif "h265" in raw_l or "hevc" in raw_l:
        codec = "H.265"
    elif "av1" in raw_l:
        codec = "AV1"
    elif "vp8" in raw_l:
        codec = "VP8"
    elif "vp9" in raw_l:
        codec = "VP9"
    else:
        codec = "Video"
    # SW vs HW
    kind = "Software" if ("google" in raw_l or "c2.android" in raw_l or "sw" in raw_l) else "Hardware"
    return f"{codec} {kind} ({vendor})"


def fetch_encoders(app, serial: str) -> None:
    """Ambil daftar encoder dari device via scrcpy --list-encoders (background)."""
    def _run():
        raw_list = []
        try:
            r = subprocess.run(
                ["scrcpy", "-s", serial, "--list-encoders"],
                capture_output=True, text=True, timeout=10)
            for line in (r.stdout + r.stderr).splitlines():
                line = line.strip()
                if "--video-encoder=" in line:
                    enc = line.split("--video-encoder=")[-1].strip().split()[0]
                    if enc:
                        raw_list.append(enc)
        except Exception:
            pass
        app.after(0, lambda: set_encoder_list(app, raw_list))
    threading.Thread(target=_run, daemon=True).start()


def set_encoder_list(app, raw_list: list) -> None:
    """Update combo encoder dengan label simpel + simpan mapping ke raw name."""
    global ENCODER_LABEL_MAP
    if not hasattr(app, "combo_encoder"):
        return

    label_map: dict = {"(auto)": ""}
    seen_labels: dict = {}
    for raw in raw_list:
        lbl = encoder_label(raw)
        if lbl in seen_labels:
            seen_labels[lbl] += 1
            lbl = f"{lbl} #{seen_labels[lbl]}"
        else:
            seen_labels[lbl] = 1
        label_map[lbl] = raw

    ENCODER_LABEL_MAP = label_map
    labels = list(label_map.keys())
    app.combo_encoder.configure(values=labels)

    # Pertahankan pilihan sebelumnya jika masih ada
    current_raw = app.V["video_encoder"].get()
    matched = next((lbl for lbl, raw in label_map.items() if raw == current_raw), None)
    app.V["video_encoder"].set(matched if matched else "(auto)")

    count = len(raw_list)
    hint  = f"{count} encoder(s) found" if count > 0 else "not detected"
    if hasattr(app, "lbl_encoder_hint"):
        app.lbl_encoder_hint.configure(text=hint)


# ── Start All button ──────────────────────────────────────────────────────────

def update_start_all_btn(app, count: int) -> None:
    """Enable/disable tombol Start All berdasarkan jumlah device."""
    if not hasattr(app, "btn_start_all"):
        return
    if count > 1:
        app.btn_start_all.configure(state="normal",   fg_color=adb_manager.GRN,   hover_color="#28a745")
    else:
        app.btn_start_all.configure(state="disabled", fg_color=adb_manager.CARD2, hover_color=adb_manager.CARD2)
