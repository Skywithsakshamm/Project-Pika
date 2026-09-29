"""
Local memory store for Selvie.
Maintains persistent non-sensitive user context, habits, preferences, and workflows.
Blocks credentials, API keys, passwords, and sensitive tokens.
"""
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
from backend.database.db import get_db_connection

FORBIDDEN_PATTERNS = [
    r'(?i)password',
    r'(?i)passwd',
    r'(?i)secret',
    r'(?i)api[-_]?key',
    r'(?i)bearer',
    r'(?i)token',
    r'(?i)auth',
    r'(?i)private[-_]?key',
    r'(?i)pin\b',
    r'(?i)credit[-_]?card',
    r'(?i)cvv\b'
]

class MemoryManager:
    @staticmethod
    def _is_sensitive(text: str) -> bool:
        for p in FORBIDDEN_PATTERNS:
            if re.search(p, text):
                return True
        return False

    @classmethod
    def remember(cls, key: str, content: str, category: str = "preference") -> Dict[str, Any]:
        """Store or update a non-sensitive fact/preference."""
        if cls._is_sensitive(key) or cls._is_sensitive(content):
            return {
                "success": False,
                "message": "For your safety, Selvie does not store passwords, keys, or sensitive credentials."
            }

        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO memories (key, category, content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET 
                content = excluded.content,
                category = excluded.category,
                updated_at = excluded.updated_at
        """, (key.strip().lower(), category, content.strip(), now_str, now_str))

        conn.commit()
        conn.close()
        return {"success": True, "key": key, "content": content}

    @staticmethod
    def recall(query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve memories matching query or all memories."""
        conn = get_db_connection()
        cursor = conn.cursor()

        if query:
            search = f"%{query.strip().lower()}%"
            cursor.execute("SELECT * FROM memories WHERE key LIKE ? OR content LIKE ? ORDER BY updated_at DESC", (search, search))
        else:
            cursor.execute("SELECT * FROM memories ORDER BY updated_at DESC")

        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def forget(key_or_pattern: str) -> bool:
        """Delete specific memory by key or pattern."""
        conn = get_db_connection()
        cursor = conn.cursor()
        search = f"%{key_or_pattern.strip().lower()}%"
        cursor.execute("DELETE FROM memories WHERE key LIKE ? OR content LIKE ?", (search, search))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count > 0

    @staticmethod
    def clear_all() -> bool:
        """Delete all memories."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE key != 'user_name'")
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_context_summary() -> str:
        """Format stored memories into a compact context string for the LLM brain."""
        memories = MemoryManager.recall()
        if not memories:
            return "No previous memories stored."
        lines = []
        for m in memories:
            lines.append(f"- {m['key']}: {m['content']}")
        return "\n".join(lines)

memory_manager = MemoryManager()
