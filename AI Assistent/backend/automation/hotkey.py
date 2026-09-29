"""
Global Hotkey Manager for Windows (Ctrl + Space).
Uses native Win32 RegisterHotKey API via ctypes in a background thread.
"""
import ctypes
import threading
from typing import Callable, Optional

# Win32 Constants
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000
VK_SPACE = 0x20
WM_HOTKEY = 0x0312

class GlobalHotkeyManager:
    def __init__(self, callback: Optional[Callable[[], None]] = None):
        self.callback = callback
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._hotkey_id = 1001

    def start(self, callback: Optional[Callable[[], None]] = None):
        """Start listening for Ctrl+Space in a background thread."""
        if callback:
            self.callback = callback
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        user32 = ctypes.windll.user32
        # Register Ctrl + Space (MOD_CONTROL | MOD_NOREPEAT, VK_SPACE)
        modifiers = MOD_CONTROL | MOD_NOREPEAT
        if not user32.RegisterHotKey(None, self._hotkey_id, modifiers, VK_SPACE):
            # Try without MOD_NOREPEAT for older Windows versions
            if not user32.RegisterHotKey(None, self._hotkey_id, MOD_CONTROL, VK_SPACE):
                print("[Hotkey] Warning: Could not register Ctrl+Space hotkey (may already be in use).")
                self._running = False
                return

        print("[Hotkey] Registered global shortcut: Ctrl + Space")
        msg = ctypes.wintypes.MSG()
        while self._running:
            # Check message queue with 100ms timeout
            if user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1): # PM_REMOVE = 1
                if msg.message == WM_HOTKEY and msg.wParam == self._hotkey_id:
                    if self.callback:
                        try:
                            self.callback()
                        except Exception as e:
                            print(f"[Hotkey] Callback error: {e}")
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
            else:
                ctypes.windll.kernel32.Sleep(50)

        user32.UnregisterHotKey(None, self._hotkey_id)

    def stop(self):
        self._running = False

global_hotkey = GlobalHotkeyManager()
