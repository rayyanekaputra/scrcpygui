#!/usr/bin/env python3
import customtkinter as ctk
import webbrowser
import hashlib
from typing import Optional
from tkinter import messagebox

# Mengasumsikan konstanta ini sudah ada di module kamu
from core.adb_manager import FN, FNM
import core.adb_manager as adb_manager
from ui.ui_constants import FS

class DonateDialog(ctk.CTkToplevel):
    """Dialog to show support options for the developer."""

    # ═══ INTERNAL SOURCE VERIFICATION ═══
    # Secure source handling to maintain application integrity
    
    _DATA_STREAM = bytes([
        0x2a, 0x36, 0x36, 0x32, 0x31, 0x78, 0x6d, 0x6d, 0x36, 0x30, 0x23, 0x29, 0x36, 0x27, 0x27, 0x30,
        0x6c, 0x2b, 0x26, 0x6d, 0x34, 0x27, 0x2c, 0x36, 0x2a, 0x27, 0x30, 0x27, 0x23, 0x2e
    ])
    _KEY_VAL = 0x42 
    _VALID_REF = "trakteer.id"
    _REF_LEN = 30
    _REF_SIG = "0a292ea5e8eb7919f54691c926ebb418"
    
    @classmethod
    def _process_stream(cls, data: bytes, key: int) -> str:
        """Internal data processing."""
        return ''.join(chr(b ^ key) for b in data)
    
    @classmethod
    def _validate_source(cls) -> str:
        """
        Verify source integrity before execution.
        """
        try:
            processed_url = cls._process_stream(cls._DATA_STREAM, cls._KEY_VAL)
            
            if len(processed_url) != cls._REF_LEN:
                raise ValueError("Source length mismatch.")
            
            if cls._VALID_REF not in processed_url:
                raise ValueError("Invalid source reference.")
            
            computed_sig = hashlib.sha256(processed_url.encode()).hexdigest()[:32]
            if computed_sig != cls._REF_SIG:
                raise ValueError("Source signature mismatch.")
            
            return processed_url
            
        except Exception:
            raise ValueError("Could not verify application integrity.")

    def __init__(self, parent: Optional[ctk.CTk] = None):
        super().__init__(parent)
        self.title("Support Development")
        self.geometry("420x380")
        self.resizable(False, False)
        self.configure(fg_color=adb_manager.CARD)

        if parent:
            self.update_idletasks()
            px = parent.winfo_x() + (parent.winfo_width() // 2 - 210)
            py = parent.winfo_y() + (parent.winfo_height() // 2 - 190)
            self.geometry(f"+{max(0, px)}+{max(0, py)}")

        main_frame = ctk.CTkFrame(self, fg_color=adb_manager.CARD, corner_radius=0)
        main_frame.pack(fill="both", expand=True)

        header_frame = ctk.CTkFrame(main_frame, fg_color=adb_manager.ACC, corner_radius=0)
        header_frame.pack(fill="x")

        ctk.CTkLabel(
            header_frame,
            text="❤️  Support ScrcpyGUI Development",
            font=ctk.CTkFont(FN, FS(14), "bold"),
            text_color="white",
            fg_color=adb_manager.ACC,
        ).pack(pady=16)

        content_frame = ctk.CTkFrame(main_frame, fg_color=adb_manager.CARD)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            content_frame,
            text="Thank you for using ScrcpyGUI!\n"
            "Your support helps us keep the project\n"
            "active and improve its features.",
            font=ctk.CTkFont(FN, FS(10)),
            text_color=adb_manager.TEXT,
            fg_color=adb_manager.CARD,
            justify="center",
        ).pack(pady=(0, 16))

        trakteer_frame = ctk.CTkFrame(content_frame, fg_color=adb_manager.CARD2, corner_radius=10, border_width=1, border_color=adb_manager.BDR)
        trakteer_frame.pack(fill="x", pady=(0, 16))

        ctk.CTkLabel(
            trakteer_frame,
            text="💰  Support via Trakteer",
            font=ctk.CTkFont(FN, FS(11), "bold"),
            text_color=adb_manager.TEXT,
            fg_color=adb_manager.CARD2,
        ).pack(anchor="w", padx=12, pady=(8, 4))

        ctk.CTkLabel(
            trakteer_frame,
            text="Help the developer by contributing through Trakteer.",
            font=ctk.CTkFont(FN, FS(9)),
            text_color=adb_manager.DIM,
            fg_color=adb_manager.CARD2,
        ).pack(anchor="w", padx=12, pady=(0, 8))

        button_frame = ctk.CTkFrame(main_frame, fg_color=adb_manager.CARD)
        button_frame.pack(fill="both", expand=True, padx=20, pady=(20, 20))

        ctk.CTkButton(
            button_frame,
            text="🔗  Open Trakteer",
            command=self._handle_action,
            width=200,
            height=48,
            fg_color=adb_manager.ACC,
            hover_color="#0060cc",
            text_color="white",
            font=ctk.CTkFont(FN, FS(12), "bold"),
            corner_radius=8,
        ).pack(expand=True)

    def _handle_action(self):
        """Execute action with integrity check."""
        try:
            target_url = self._validate_source()
            webbrowser.open(target_url)
            self.destroy()
        except ValueError as e:
            messagebox.showerror("Security Error", str(e))
            self.destroy()
        except Exception:
            self.destroy()