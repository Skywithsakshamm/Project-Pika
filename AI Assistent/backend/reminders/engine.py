"""
Reminder Engine for Selvie.
Provides background timer checking, Windows toast notifications, and voice alerts.
"""
import re
import threading
import time
import subprocess
import winsound
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional, Callable
from backend.database.db import get_db_connection

class ReminderEngine:
    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []

    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback when a reminder triggers (e.g., for TTS or WebSocket push)."""
        self._callbacks.append(callback)

    def start(self):
        """Start the reminder background loop."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def create_reminder(
        self,
        message: str,
        trigger_time_str: str,
        is_recurring: bool = False,
        repeat_pattern: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new reminder.
        trigger_time_str can be:
        - ISO datetime: "2026-09-30T19:00:00"
        - Time of day: "19:00", "7:00 PM", "7 PM"
        - Relative: "+30m", "+2h"
        """
        parsed_dt = self._parse_time(trigger_time_str)

        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO reminders (message, trigger_time, is_recurring, repeat_pattern, is_active, created_at)
            VALUES (?, ?, ?, ?, 1, ?)
        """, (message.strip(), parsed_dt.isoformat(), 1 if is_recurring else 0, repeat_pattern, now_str))

        reminder_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return self.get_reminder(reminder_id)

    def get_reminder(self, reminder_id: int) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def get_active_reminders(self) -> List[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reminders WHERE is_active = 1 ORDER BY trigger_time ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_reminder(self, reminder_id: int) -> bool:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        conn.commit()
        conn.close()
        return True

    def _loop(self):
        while self._running:
            try:
                now_iso = datetime.now().isoformat()
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM reminders 
                    WHERE is_active = 1 AND trigger_time <= ?
                """, (now_iso,))
                due_reminders = [dict(r) for r in cursor.fetchall()]

                for r in due_reminders:
                    # Mark inactive or reschedule
                    if r["is_recurring"]:
                        # e.g., daily repeat
                        next_dt = datetime.fromisoformat(r["trigger_time"]) + timedelta(days=1)
                        cursor.execute("UPDATE reminders SET trigger_time = ?, triggered_at = ? WHERE id = ?",
                                       (next_dt.isoformat(), now_iso, r["id"]))
                    else:
                        cursor.execute("UPDATE reminders SET is_active = 0, triggered_at = ? WHERE id = ?",
                                       (now_iso, r["id"]))
                    conn.commit()

                    # Trigger notification & callbacks
                    self._dispatch_alert(r)

                conn.close()
            except Exception as e:
                print(f"[ReminderEngine] Error in loop: {e}")

            time.sleep(3)

    def _dispatch_alert(self, reminder: Dict[str, Any]):
        msg = reminder.get("message", "Reminder")
        # 1. Play subtle audio ding
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        # 2. Windows toast notification
        self._show_windows_toast("Selvie Reminder", msg)

        # 3. Notify callbacks (TTS voice announcement + WebSocket push)
        for cb in self._callbacks:
            try:
                cb(reminder)
            except Exception as e:
                print(f"[ReminderEngine] Callback error: {e}")

    @staticmethod
    def _show_windows_toast(title: str, message: str):
        """Show a native Windows notification using PowerShell."""
        clean_title = title.replace('"', '`"')
        clean_msg = message.replace('"', '`"')
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $textNodes = $template.GetElementsByTagName("text")
        $textNodes.Item(0).AppendChild($template.CreateTextNode("{clean_title}")) | Out-Null
        $textNodes.Item(1).AppendChild($template.CreateTextNode("{clean_msg}")) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Selvie AI Assistant")
        $notifier.Show($toast)
        """
        try:
            subprocess.Popen(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps_script],
                             creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0)
        except Exception as e:
            print(f"[ReminderEngine] Toast notification fallback error: {e}")

    @staticmethod
    def _parse_time(time_str: str) -> datetime:
        """Parse natural time or explicit timestamp into a datetime object."""
        now = datetime.now()
        s = time_str.strip().lower()

        # Check relative formats: e.g. "in 30 minutes", "in 2 hours", "+30m", "+1h"
        rel_match = re.search(r'(?:in\s+)?(\d+)\s*(m|min|minute|minutes|h|hr|hour|hours|s|sec|seconds?)', s)
        if rel_match:
            val = int(rel_match.group(1))
            unit = rel_match.group(2)
            if unit.startswith('m'):
                return now + timedelta(minutes=val)
            elif unit.startswith('h'):
                return now + timedelta(hours=val)
            elif unit.startswith('s'):
                return now + timedelta(seconds=val)

        # Check explicit times: e.g. "7:00 pm", "7 pm", "19:00", "07:30"
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', s)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            meridiem = time_match.group(3)

            if meridiem:
                if meridiem == 'pm' and hour < 12:
                    hour += 12
                elif meridiem == 'am' and hour == 12:
                    hour = 0

            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            # If target is already in the past today, assume tomorrow
            if target <= now:
                target += timedelta(days=1)
            return target

        # Default fallback: 1 hour from now
        return now + timedelta(hours=1)

reminder_engine = ReminderEngine()
