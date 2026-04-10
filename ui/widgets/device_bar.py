"""Device Selection Bar Widget"""

import customtkinter as ctk  # type: ignore
from core.adb_manager import FN
import core.adb_manager as adb_manager
from ui.ui_constants import FS


class DeviceBar(ctk.CTkFrame):
    """Reusable device selection and refresh bar."""

    def __init__(self, parent, device_var, on_device_selected, on_refresh):
        """
        Initialize device bar.
        
        Args:
            parent: Parent widget
            device_var: StringVar for device selection
            on_device_selected: Callback(value) when device selected
            on_refresh: Callback() when refresh clicked
        """
        super().__init__(parent, fg_color=adb_manager.BG)

        ctk.CTkLabel(
            self,
            text="DEVICE",
            font=ctk.CTkFont(FN, FS(9), "bold"),
            text_color=adb_manager.DIM,
            fg_color=adb_manager.BG
        ).pack(side="left", padx=(0, 8))

        self.combo_device = ctk.CTkComboBox(
            self,
            values=[],
            variable=device_var,
            width=320,
            font=ctk.CTkFont("Monospace", FS(10)),
            fg_color=adb_manager.CARD,
            border_color=adb_manager.BDR,
            button_color=adb_manager.ACC,
            dropdown_fg_color=adb_manager.CARD,
            dropdown_text_color=adb_manager.TEXT,
            text_color=adb_manager.TEXT,
            state="readonly",
            command=on_device_selected
        )
        self.combo_device.pack(side="left", padx=(0, 8))

        self.btn_refresh = ctk.CTkButton(
            self,
            text="↺  Refresh",
            command=on_refresh,
            width=110,
            height=32,
            fg_color=adb_manager.CARD,
            hover_color="#45475a",
            text_color=adb_manager.ACC,
            font=ctk.CTkFont(FN, FS(10), "bold"),
            border_width=1,
            border_color=adb_manager.BDR,
            corner_radius=8
        )
        self.btn_refresh.pack(side="left", padx=(0, 8))

        self.lbl_info = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(FN, FS(9)),
            text_color=adb_manager.DIM,
            fg_color=adb_manager.BG
        )
        self.lbl_info.pack(side="left")

    def set_devices(self, values: list):
        """Update combo values."""
        self.combo_device.configure(values=values)

    def set_info(self, text: str):
        """Update info label."""
        self.lbl_info.configure(text=text)
