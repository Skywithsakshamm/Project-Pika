"""
Safe Application, Website, Folder, and Media Launcher for Selvie on Windows.
Executes controlled operations using native Windows APIs and protocol handlers.
"""
import os
import sys
import json
import webbrowser
import subprocess
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional
from backend.database.db import get_db_connection

# Windows media virtual keys
VK_MEDIA_NEXT_TRACK = 0xB0
VK_MEDIA_PREV_TRACK = 0xB1
VK_MEDIA_STOP = 0xB2
VK_MEDIA_PLAY_PAUSE = 0xB3

class AppLauncher:
    @staticmethod
    def _send_media_key(vk_code: int):
        """Simulate Windows media key press using win32api or ctypes."""
        try:
            import win32api
            import win32con
            win32api.keybd_event(vk_code, 0, 0, 0)
            win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
            return True
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
                ctypes.windll.user32.keybd_event(vk_code, 0, 2, 0)
                return True
            except Exception as e:
                print(f"[Launcher] Failed to send media key: {e}")
                return False

    @staticmethod
    def open_application(app_name: str) -> Dict[str, Any]:
        """Launch an application from registry or known Windows system apps."""
        clean_name = app_name.strip().lower()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM app_registry")
        apps = [dict(r) for r in cursor.fetchall()]
        conn.close()

        matched_app = None
        for app in apps:
            if app["name"].lower() == clean_name:
                matched_app = app
                break
            aliases = json.loads(app.get("aliases", "[]"))
            if any(alias.lower() == clean_name or alias.lower() in clean_name for alias in aliases):
                matched_app = app
                break

        if matched_app:
            cmd = matched_app["command"]
            uri = matched_app.get("uri_scheme", "")

            # If it's a web URL
            if cmd.startswith("http://") or cmd.startswith("https://"):
                webbrowser.open(cmd)
                return {"success": True, "app": matched_app["name"], "type": "url", "message": f"Opening {matched_app['name']}"}

            # If it's a URI scheme (like spotify:, whatsapp:, ms-settings:)
            if uri and (uri.endswith(":") or uri.startswith("ms-") or uri.startswith("whatsapp:")):
                try:
                    os.startfile(uri)
                    return {"success": True, "app": matched_app["name"], "type": "uri", "message": f"Opening {matched_app['name']}"}
                except Exception:
                    pass

            # Otherwise launch executable/command
            try:
                subprocess.Popen(cmd, shell=True)
                return {"success": True, "app": matched_app["name"], "type": "process", "message": f"Launching {matched_app['name']}"}
            except Exception as e:
                # Try os.startfile fallback
                try:
                    os.startfile(cmd)
                    return {"success": True, "app": matched_app["name"], "type": "startfile", "message": f"Opening {matched_app['name']}"}
                except Exception as ex:
                    return {"success": False, "app": matched_app["name"], "error": str(ex), "message": f"Could not launch {matched_app['name']}."}

        # Check common system commands directly
        system_map = {
            "notepad": "notepad.exe",
            "calc": "calc.exe",
            "calculator": "calc.exe",
            "explorer": "explorer.exe",
            "terminal": "wt.exe",
            "powershell": "powershell.exe",
            "cmd": "cmd.exe",
            "paint": "mspaint.exe",
            "task manager": "taskmgr.exe"
        }

        if clean_name in system_map:
            try:
                subprocess.Popen(system_map[clean_name], shell=True)
                return {"success": True, "app": clean_name, "message": f"Opened {clean_name}"}
            except Exception as e:
                return {"success": False, "app": clean_name, "error": str(e)}

        return {
            "success": False,
            "app": app_name,
            "message": f"I don't have '{app_name}' configured yet. Want me to help you add it?"
        }

    @staticmethod
    def register_custom_app(name: str, command: str, aliases: List[str] = None, category: str = "Custom") -> Dict[str, Any]:
        """Register a user custom app path or command."""
        conn = get_db_connection()
        cursor = conn.cursor()
        alias_list = aliases or [name.lower()]
        cursor.execute("""
            INSERT OR REPLACE INTO app_registry (name, aliases, command, uri_scheme, icon, category)
            VALUES (?, ?, ?, ?, 'grid', ?)
        """, (name, json.dumps(alias_list), command, "", category))
        conn.commit()
        conn.close()
        return {"success": True, "name": name, "command": command}

    @staticmethod
    def list_registered_apps() -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM app_registry ORDER BY name ASC")
        rows = cursor.fetchall()
        conn.close()
        result = []
        for r in rows:
            d = dict(r)
            d["aliases"] = json.loads(d.get("aliases", "[]"))
            result.append(d)
        return result

    @staticmethod
    def open_website(url: str) -> Dict[str, Any]:
        """Open a website URL in default browser."""
        target = url.strip()
        if not target.startswith("http://") and not target.startswith("https://"):
            target = "https://" + target
        webbrowser.open(target)
        return {"success": True, "url": target, "message": f"Opened {target}"}

    @staticmethod
    def search_web(query: str, engine: str = "google") -> Dict[str, Any]:
        """Search Google or YouTube for a query."""
        encoded = urllib.parse.quote_plus(query.strip())
        if engine.lower() == "youtube":
            url = f"https://www.youtube.com/results?search_query={encoded}"
        else:
            url = f"https://www.google.com/search?q={encoded}"
        webbrowser.open(url)
        return {"success": True, "query": query, "url": url, "message": f"Searching {engine} for '{query}'"}

    @staticmethod
    def play_media(query: str = "", platform: str = "auto") -> Dict[str, Any]:
        """
        Play music/playlists on YouTube or Spotify.
        Also supports pause/resume/next commands.
        """
        q = query.strip().lower()

        # Check media controls
        if q in ["pause", "stop", "unpause", "play", "toggle"]:
            AppLauncher._send_media_key(VK_MEDIA_PLAY_PAUSE)
            return {"success": True, "action": "toggle_playback", "message": "Toggled media playback."}
        if q in ["next", "next track", "skip", "next song"]:
            AppLauncher._send_media_key(VK_MEDIA_NEXT_TRACK)
            return {"success": True, "action": "next_track", "message": "Playing next song."}
        if q in ["previous", "prev", "back"]:
            AppLauncher._send_media_key(VK_MEDIA_PREV_TRACK)
            return {"success": True, "action": "prev_track", "message": "Playing previous song."}

        # If Spotify specified or preferred
        if "spotify" in platform.lower() or "spotify" in q:
            clean_q = q.replace("spotify", "").replace("play", "").strip()
            # Try launching spotify URI search
            if clean_q:
                encoded = urllib.parse.quote(clean_q)
                uri = f"spotify:search:{encoded}"
                try:
                    os.startfile(uri)
                    return {"success": True, "platform": "spotify", "query": clean_q, "message": f"Playing '{clean_q}' on Spotify."}
                except Exception:
                    pass
            else:
                try:
                    os.startfile("spotify:")
                    return {"success": True, "platform": "spotify", "message": "Opened Spotify."}
                except Exception:
                    pass

        # Default to YouTube study/focus music search
        search_term = query if query else "relaxing study focus music"
        encoded = urllib.parse.quote_plus(search_term)
        url = f"https://www.youtube.com/results?search_query={encoded}"
        webbrowser.open(url)
        return {
            "success": True,
            "platform": "youtube",
            "query": search_term,
            "url": url,
            "message": f"Opening YouTube and finding {search_term}."
        }

    @staticmethod
    def open_folder(folder_name_or_path: str) -> Dict[str, Any]:
        """Open a folder in Windows File Explorer safely."""
        target_path = folder_name_or_path.strip().strip('"').strip("'")
        user_home = Path.home()

        folder_aliases = {
            "projects": user_home / "Desktop" / "Project Pika",
            "project pika": user_home / "Desktop" / "Project Pika",
            "selvie": Path(__file__).resolve().parent.parent.parent,
            "desktop": user_home / "Desktop",
            "downloads": user_home / "Downloads",
            "documents": user_home / "Documents",
            "music": user_home / "Music",
            "pictures": user_home / "Pictures",
            "college": user_home / "Desktop" / "College",
        }

        key = target_path.lower()
        if key in folder_aliases and folder_aliases[key].exists():
            resolved = folder_aliases[key]
        else:
            p = Path(target_path)
            if not p.is_absolute():
                p = user_home / target_path
            resolved = p

        if not resolved.exists():
            # Create folder if asked or return helpful message
            return {"success": False, "path": str(resolved), "message": f"Folder '{target_path}' doesn't exist yet."}

        try:
            os.startfile(str(resolved))
            return {"success": True, "path": str(resolved), "message": f"Opened folder {resolved.name}."}
        except Exception as e:
            return {"success": False, "error": str(e), "message": f"Could not open folder: {e}"}

    @staticmethod
    def create_folder(folder_path: str) -> Dict[str, Any]:
        """Create a new folder safely."""
        p = Path(folder_path)
        if not p.is_absolute():
            p = Path.home() / "Desktop" / folder_path
        try:
            p.mkdir(parents=True, exist_ok=True)
            return {"success": True, "path": str(p), "message": f"Created folder '{p.name}' at {p}."}
        except Exception as e:
            return {"success": False, "error": str(e), "message": f"Could not create folder: {e}"}

    @staticmethod
    def create_file(file_path: str, content: str = "") -> Dict[str, Any]:
        """Create a text file safely."""
        p = Path(file_path)
        if not p.is_absolute():
            p = Path.home() / "Desktop" / file_path
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(content)
            return {"success": True, "path": str(p), "message": f"Created file '{p.name}'."}
        except Exception as e:
            return {"success": False, "error": str(e), "message": f"Could not create file: {e}"}

app_launcher = AppLauncher()
