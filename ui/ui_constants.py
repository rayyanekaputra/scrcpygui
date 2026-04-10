"""UI Constants - styling, fonts, presets, and UI helpers."""

from typing import Dict, List

PALETTE_DARK = {
    "BG":"#1c1c1e","CARD":"#2c2c2e","CARD2":"#3a3a3c",
    "BDR":"#48484a","TEXT":"#ffffff","DIM":"#ebebf5",
}
PALETTE_LIGHT = {
    "BG":"#f2f2f7","CARD":"#ffffff","CARD2":"#e5e5ea",
    "BDR":"#c7c7cc","TEXT":"#000000","DIM":"#3a3a3c",
}

BG: str = PALETTE_DARK["BG"]
CARD: str = PALETTE_DARK["CARD"]
CARD2: str = PALETTE_DARK["CARD2"]
BDR: str = PALETTE_DARK["BDR"]
TEXT: str = PALETTE_DARK["TEXT"]
DIM: str = PALETTE_DARK["DIM"]

ACC: str = "#0a84ff"
RED: str = "#ff453a"
YEL: str = "#ffd60a"
GRN: str = "#30d158"
FN: str = "DejaVu Sans"
FNM: str = "DejaVu Sans Mono"

MODES: List[str] = ["Mirror Only", "Record", "Livestream"]
PLATFORM_RTMP: Dict[str, str] = {
    "YouTube": "rtmp://a.rtmp.youtube.com/live2/",
    "Custom":  "",
}

PRESETS = {
    "Performance": {
        "bitrate":"8M","max_fps":"60","resolution":"1080","codec":"h264",
        "borderless":True,"always_on_top":True,"stay_awake":True,
        "turn_screen_off":True,"fullscreen":False,"no_audio":False,"no_control":False,
    },
    "Balanced": {
        "bitrate":"4M","max_fps":"30","resolution":"720","codec":"h264",
        "borderless":True,"always_on_top":False,"stay_awake":True,
        "turn_screen_off":False,"fullscreen":False,"no_audio":False,"no_control":False,
    },
    "Saver": {
        "bitrate":"2M","max_fps":"24","resolution":"480","codec":"h264",
        "borderless":False,"always_on_top":False,"stay_awake":True,
        "turn_screen_off":True,"fullscreen":False,"no_audio":False,"no_control":False,
    },
}

# ── UI Scale (will be set at startup) ────────────────────────────────────────
UI_SCALE: float = 1.0


def FS(size: int) -> int:
    """Scale font size according to DPI."""
    return max(7, round(size * UI_SCALE))


def set_ui_scale(scale: float):
    """Update global UI_SCALE value."""
    global UI_SCALE
    UI_SCALE = max(0.75, min(2.0, scale))


# ── Recording Settings ────────────────────────────────────────────────────────────
RECORD_FILTERS = [
    ("MP4 Video", "*.mp4"),
    ("MKV Video", "*.mkv"),
    ("All Files", "*.*"),
]

# ── TCP/IP Default Port ──────────────────────────────────────────────────────────
TCPIP_DEFAULT_PORT = 5555
