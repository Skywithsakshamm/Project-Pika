"""
Task Management module for Selvie.
Handles Smart To-Do list with priorities, estimated duration, statuses, and auto-categorization.
"""
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from backend.database.db import get_db_connection

class TaskManager:
    @staticmethod
    def create_task(
        title: str,
        priority: str = "Medium",
        due_date: Optional[str] = None,
        due_time: Optional[str] = None,
        duration_minutes: int = 60,
        description: str = "",
        category: str = "General"
    ) -> Dict[str, Any]:
        """Create a new task."""
        # Normalize priority
        priority = priority.capitalize() if priority else "Medium"
        if priority not in ["High", "Medium", "Low"]:
            priority = "Medium"

        if not due_date or due_date.lower() == "today":
            due_date = date.today().isoformat()
        elif due_date.lower() == "tomorrow":
            due_date = (date.today().fromordinal(date.today().toordinal() + 1)).isoformat()

        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()

        cursor.execute("""
            INSERT INTO tasks (title, description, priority, due_date, due_time, duration_minutes, status, category, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
        """, (title.strip(), description.strip(), priority, due_date, due_time or "", duration_minutes, category, now_str))

        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return TaskManager.get_task(task_id)

    @staticmethod
    def get_task(task_id: int) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    @staticmethod
    def get_tasks(status: Optional[str] = None, priority: Optional[str] = None) -> List[Dict[str, Any]]:
        """List tasks with optional filters."""
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if priority:
            query += " AND priority = ?"
            params.append(priority)

        query += " ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END, id DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def get_today_tasks() -> List[Dict[str, Any]]:
        """Get all pending or in-progress tasks for today or overdue."""
        today_str = date.today().isoformat()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE (due_date = ? OR due_date = '' OR due_date <= ?)
              AND status IN ('Pending', 'In Progress')
            ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END, id ASC
        """, (today_str, today_str))
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]

    @staticmethod
    def complete_task(task_identifier: Any) -> Optional[Dict[str, Any]]:
        """Mark task complete by ID or fuzzy matching title."""
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()

        task_id = None
        if isinstance(task_identifier, int) or (isinstance(task_identifier, str) and task_identifier.isdigit()):
            task_id = int(task_identifier)
        else:
            # Fuzzy match title
            search_pattern = f"%{str(task_identifier).strip()}%"
            cursor.execute("SELECT id FROM tasks WHERE title LIKE ? AND status != 'Completed' LIMIT 1", (search_pattern,))
            match = cursor.fetchone()
            if match:
                task_id = match["id"]

        if not task_id:
            conn.close()
            return None

        cursor.execute("""
            UPDATE tasks 
            SET status = 'Completed', completed_at = ? 
            WHERE id = ?
        """, (now_str, task_id))
        conn.commit()
        conn.close()
        return TaskManager.get_task(task_id)

    @staticmethod
    def update_task(task_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        allowed_keys = ["title", "description", "priority", "due_date", "due_time", "duration_minutes", "status", "category"]
        valid_updates = {k: v for k, v in updates.items() if k in allowed_keys}
        if not valid_updates:
            return TaskManager.get_task(task_id)

        set_clause = ", ".join([f"{k} = ?" for k in valid_updates.keys()])
        values = list(valid_updates.values()) + [task_id]

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()
        return TaskManager.get_task(task_id)

    @staticmethod
    def delete_task(task_identifier: Any) -> bool:
        """Delete task by ID or title match."""
        conn = get_db_connection()
        cursor = conn.cursor()

        task_id = None
        if isinstance(task_identifier, int) or (isinstance(task_identifier, str) and task_identifier.isdigit()):
            task_id = int(task_identifier)
        else:
            search_pattern = f"%{str(task_identifier).strip()}%"
            cursor.execute("SELECT id FROM tasks WHERE title LIKE ? LIMIT 1", (search_pattern,))
            match = cursor.fetchone()
            if match:
                task_id = match["id"]

        if not task_id:
            conn.close()
            return False

        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return True

    @staticmethod
    def get_summary() -> Dict[str, Any]:
        """Summary of pending vs completed tasks with stress indicators."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, priority, count(*) as count FROM tasks GROUP BY status, priority")
        rows = cursor.fetchall()
        conn.close()

        summary = {"total_pending": 0, "high_priority": 0, "medium_priority": 0, "low_priority": 0, "completed": 0}
        for r in rows:
            if r["status"] in ["Pending", "In Progress"]:
                summary["total_pending"] += r["count"]
                if r["priority"] == "High":
                    summary["high_priority"] += r["count"]
                elif r["priority"] == "Medium":
                    summary["medium_priority"] += r["count"]
                elif r["priority"] == "Low":
                    summary["low_priority"] += r["count"]
            elif r["status"] == "Completed":
                summary["completed"] += r["count"]

        # Stress indicator
        summary["is_overwhelmed"] = summary["total_pending"] > 6
        return summary

task_manager = TaskManager()
