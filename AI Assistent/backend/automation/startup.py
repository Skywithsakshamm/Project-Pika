"""
Windows Startup Configuration for Selvie.
Manages HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run registry key.
"""
import sys
import winreg
from pathlib import Path

REG_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "SelvieAIAssistant"

class StartupManager:
    @staticmethod
    def is_startup_enabled() -> bool:
        """Check if Selvie is registered in Windows startup registry."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, APP_NAME)
            winreg.CloseKey(key)
            return bool(val)
        except WindowsError:
            return False

    @staticmethod
    def enable_startup(launch_cmd: str = None) -> bool:
        """Add Selvie to Windows startup."""
        if not launch_cmd:
            # Default to running launcher bat or python script
            base_dir = Path(__file__).resolve().parent.parent.parent
            bat_path = base_dir / "run_selvie.bat"
            if bat_path.exists():
                launch_cmd = f'"{bat_path}" --background'
            else:
                py_path = base_dir / "run_selvie.py"
                launch_cmd = f'"{sys.executable}" "{py_path}" --background'

        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, launch_cmd)
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"[StartupManager] Failed to enable startup: {e}")
            return False

    @staticmethod
    def disable_startup() -> bool:
        """Remove Selvie from Windows startup."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY, 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, APP_NAME)
            winreg.CloseKey(key)
            return True
        except WindowsError:
            return True
        except Exception as e:
            print(f"[StartupManager] Failed to disable startup: {e}")
            return False

startup_manager = StartupManager()
