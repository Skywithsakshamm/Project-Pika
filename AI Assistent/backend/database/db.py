"""
SQLite database initialization, schemas, and connection helpers for Selvie.
"""
import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path
from config.settings import settings

def get_db_connection():
    """Get a thread-safe sqlite3 connection with dict-like row access."""
    settings.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize tables and default seed records."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tasks Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT DEFAULT '',
        priority TEXT DEFAULT 'Medium',
        due_date TEXT DEFAULT '',
        due_time TEXT DEFAULT '',
        duration_minutes INTEGER DEFAULT 60,
        status TEXT DEFAULT 'Pending',
        category TEXT DEFAULT 'General',
        created_at TEXT NOT NULL,
        completed_at TEXT DEFAULT ''
    )
    """)

    # Schedules Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT NOT NULL UNIQUE,
        time_blocks TEXT NOT NULL,
        notes TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)

    # Reminders Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL,
        trigger_time TEXT NOT NULL,
        is_recurring INTEGER DEFAULT 0,
        repeat_pattern TEXT DEFAULT '',
        is_active INTEGER DEFAULT 1,
        triggered_at TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)

    # Memories Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT NOT NULL UNIQUE,
        category TEXT DEFAULT 'preference',
        content TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    # App Registry Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        aliases TEXT NOT NULL,
        command TEXT NOT NULL,
        uri_scheme TEXT DEFAULT '',
        icon TEXT DEFAULT '',
        category TEXT DEFAULT 'App'
    )
    """)

    # Settings Store Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS settings_store (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """)

    # Conversations Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)

    conn.commit()

    # Seed Default Applications if empty
    cursor.execute("SELECT COUNT(*) FROM app_registry")
    if cursor.fetchone()[0] == 0:
        default_apps = [
            ("YouTube", ["youtube", "yt"], "https://www.youtube.com", "https://www.youtube.com", "youtube", "Web"),
            ("Spotify", ["spotify", "music player"], "spotify:", "spotify:", "spotify", "Media"),
            ("WhatsApp", ["whatsapp", "wa"], "whatsapp:", "whatsapp:", "message-circle", "Social"),
            ("Chrome", ["chrome", "google chrome", "browser"], "chrome", "https://", "chrome", "Browser"),
            ("VS Code", ["vs code", "vscode", "code editor", "visual studio code"], "code", "", "code", "Development"),
            ("Notion", ["notion", "notes"], "notion:", "https://www.notion.so", "book-open", "Productivity"),
            ("Discord", ["discord", "chat"], "discord:", "discord:", "message-square", "Social"),
            ("File Explorer", ["file explorer", "explorer", "files", "my computer"], "explorer", "", "folder", "System"),
            ("Windows Settings", ["settings", "windows settings", "system settings"], "start ms-settings:", "ms-settings:", "settings", "System"),
            ("GitHub", ["github", "gh", "git"], "https://github.com", "https://github.com", "github", "Web"),
            ("ChatGPT", ["chatgpt", "chat gpt", "openai"], "https://chatgpt.com", "https://chatgpt.com", "bot", "Web"),
            ("Gmail", ["gmail", "google mail", "email"], "https://mail.google.com", "https://mail.google.com", "mail", "Web"),
            ("Google Drive", ["google drive", "drive"], "https://drive.google.com", "https://drive.google.com", "hard-drive", "Web"),
        ]
        for name, aliases, cmd, uri, icon, cat in default_apps:
            cursor.execute(
                "INSERT INTO app_registry (name, aliases, command, uri_scheme, icon, category) VALUES (?, ?, ?, ?, ?, ?)",
                (name, json.dumps(aliases), cmd, uri, icon, cat)
            )
        conn.commit()

    # Seed initial user memory
    cursor.execute("SELECT COUNT(*) FROM memories")
    if cursor.fetchone()[0] == 0:
        now_str = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO memories (key, category, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("user_name", "profile", "Saksham", now_str, now_str)
        )
        cursor.execute(
            "INSERT INTO memories (key, category, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("preferred_style", "preference", "Focused, friendly, calm, Hinglish-friendly, stress-reducing", now_str, now_str)
        )
        conn.commit()

    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at", settings.DB_PATH)
