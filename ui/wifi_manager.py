"""WiFi manager for TCP/IP device connections.

This module keeps WiFi-related actions in a dedicated helper class while
still allowing access to the main app instance via self.app.
"""

import threading
from tkinter import messagebox

from core.adb_manager import enable_tcpip, detect_device_ip, connect_wifi, disconnect_wifi


class WifiManager:
    def __init__(self, app):
        self.app = app

    def _log_tcpip(self, text, tag="info"):
        def _do():
            if self.app.txt_tcpip is None:
                return
            self.app.txt_tcpip.configure(state="normal")
            tb = self.app.txt_tcpip._textbox
            tb.configure(state="normal")
            tb.insert("end", text + "\n", tag)
            tb.see("end")
            tb.configure(state="disabled")
            self.app.txt_tcpip.configure(state="disabled")

        self.app.after(0, _do)

    def _enable_tcpip(self):
        port = self.app.V["tcpip_port"].get().strip() or "5555"
        self._log_tcpip(f"$ adb tcpip {port}", "info")

        def _run():
            ok, message = enable_tcpip(port)
            if ok:
                self._log_tcpip(f"✓ {message}", "ok")
                self._log_tcpip("→ Now disconnect USB and enter device IP below", "info")
            else:
                self._log_tcpip(f"Error: {message}", "error")

        threading.Thread(target=_run, daemon=True).start()

    def _auto_detect_ip(self):
        serial = None
        for s in list(self.app.running_devs) + list(self.app.processes.keys()):
            if "." not in s:
                serial = s
                break

        if not serial:
            dev = self.app.V["device"].get()
            if dev and "no devices" not in dev:
                serial = dev.split()[0]

        if not serial:
            self._log_tcpip("Error: No USB device connected!", "error")
            return

        self._log_tcpip(f"$ adb -s {serial} shell ip addr show wlan0", "info")

        def _run():
            ok, message = detect_device_ip(serial)
            if ok:
                self.app.after(0, lambda: self.app.V["tcpip_host"].set(message))
                self._log_tcpip(f"✓ Found IP: {message}", "ok")
            else:
                self._log_tcpip(f"Error: {message}", "error")

        threading.Thread(target=_run, daemon=True).start()

    def _connect_wifi(self):
        host = self.app.V["tcpip_host"].get().strip()
        port = self.app.V["tcpip_port"].get().strip() or "5555"
        if not host:
            messagebox.showwarning("Missing IP", "Enter device IP address first!")
            return

        addr = f"{host}:{port}"
        self._log_tcpip(f"$ adb connect {addr}", "info")

        def _run():
            ok, message = connect_wifi(host, port)
            if ok:
                self._log_tcpip(f"✓ {message}", "ok")
                self._log_tcpip("→ Refresh device list in Mirror tab", "info")
                self.app.after(500, self.app._refresh_devices)
            else:
                self._log_tcpip(f"Failed: {message}", "error")

        threading.Thread(target=_run, daemon=True).start()

    def _disconnect_wifi(self):
        host = self.app.V["tcpip_host"].get().strip()
        port = self.app.V["tcpip_port"].get().strip() or "5555"
        self._log_tcpip(
            f"$ adb disconnect {host + ':' + port if host else ''}",
            "info",
        )

        def _run():
            ok, message = disconnect_wifi(host, port)
            if ok:
                self._log_tcpip(f"✓ {message}", "ok")
                self._log_tcpip("→ Reconnect USB cable if needed", "info")
                self.app.after(500, self.app._refresh_devices)
            else:
                self._log_tcpip(f"Error: {message}", "error")

        threading.Thread(target=_run, daemon=True).start()
