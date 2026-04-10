"""HiDPI Scale Detection Dialog"""

import customtkinter as ctk  # type: ignore
from core.adb_manager import FN
import core.adb_manager as adb_manager
from ui.ui_constants import FS


class HiDPIDialog(ctk.CTkToplevel):
    """Dialog for HiDPI scale adjustment."""

    def __init__(self, parent, dpi: float, suggested_scale: float, on_apply, on_skip):
        """
        Initialize HiDPI dialog.
        
        Args:
            parent: Parent window
            dpi: Detected DPI value
            suggested_scale: Suggested UI scale
            on_apply: Callback(scale) when Apply clicked
            on_skip: Callback() when Skip clicked
        """
        super().__init__(parent)

        self.title("HiDPI Detection")
        self.geometry("480x280")
        self.configure(fg_color=adb_manager.BG)
        self.resizable(False, False)

        # Header
        header = ctk.CTkFrame(self, fg_color=adb_manager.CARD, corner_radius=0)
        header.pack(fill="x", side="top")

        ctk.CTkLabel(
            header,
            text="🖥️  HiDPI Display Detected",
            font=ctk.CTkFont(FN, FS(13), "bold"),
            text_color=adb_manager.TEXT,
            fg_color=adb_manager.CARD
        ).pack(side="left", padx=16, pady=12)

        # Content frame
        content = ctk.CTkFrame(self, fg_color=adb_manager.BG)
        content.pack(fill="both", expand=True, padx=20, pady=20)

        # Info text
        ctk.CTkLabel(
            content,
            text=f"Detected DPI: {dpi:.0f}\n\nWe recommend scaling the UI to {suggested_scale:.0%} for better readability.",
            font=ctk.CTkFont(FN, FS(11)),
            text_color=adb_manager.DIM,
            fg_color=adb_manager.BG,
            justify="left"
        ).pack(anchor="w", pady=(0, 20))

        # Scale slider
        scale_frame = ctk.CTkFrame(content, fg_color=adb_manager.BG)
        scale_frame.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            scale_frame,
            text="UI Scale:",
            font=ctk.CTkFont(FN, FS(10)),
            text_color=adb_manager.TEXT,
            fg_color=adb_manager.BG
        ).pack(side="left", padx=(0, 10))

        self.scale_var = ctk.DoubleVar(value=suggested_scale * 100)
        self.scale_label = ctk.CTkLabel(
            scale_frame,
            text=f"{suggested_scale:.0%}",
            font=ctk.CTkFont(FN, FS(11), "bold"),
            text_color=adb_manager.ACC,
            fg_color=adb_manager.BG,
            width=60
        )
        self.scale_label.pack(side="right")

        self.slider = ctk.CTkSlider(
            content,
            from_=75,
            to=200,
            variable=self.scale_var,
            number_of_steps=25,
            fg_color=adb_manager.CARD,
            progress_color=adb_manager.ACC,
            button_color=adb_manager.ACC,
            button_hover_color="#0060cc",
            command=self._on_slider_change
        )
        self.slider.pack(fill="x", pady=(0, 20))

        # Buttons
        btn_frame = ctk.CTkFrame(content, fg_color=adb_manager.BG)
        btn_frame.pack(fill="x")

        ctk.CTkButton(
            btn_frame,
            text="Apply",
            command=lambda: on_apply(self.scale_var.get() / 100),
            width=150,
            height=36,
            fg_color=adb_manager.ACC,
            hover_color="#0060cc",
            text_color="white",
            font=ctk.CTkFont(FN, FS(11), "bold"),
            corner_radius=8
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            btn_frame,
            text="Skip",
            command=on_skip,
            width=150,
            height=36,
            fg_color=adb_manager.CARD2,
            hover_color=adb_manager.BDR,
            text_color=adb_manager.TEXT,
            font=ctk.CTkFont(FN, FS(11)),
            corner_radius=8
        ).pack(side="left")

        # Make modal
        self.grab_set()
        self.transient(parent)
        self.after(100, self.lift)

    def _on_slider_change(self, value: float):
        """Update scale label when slider moves."""
        self.scale_label.configure(text=f"{value / 100:.0%}")
