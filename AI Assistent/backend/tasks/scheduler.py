"""
Daily Schedule Generator with Focus Blocks and Stress-Reduction Logic for Selvie.
Builds realistic schedules with breaks, buffers, and prioritizes urgent tasks to reduce stress.
"""
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from backend.database.db import get_db_connection
from backend.tasks.manager import task_manager

class ScheduleGenerator:
    @staticmethod
    def generate_daily_schedule(target_date: Optional[str] = None, start_hour: int = 9) -> Dict[str, Any]:
        """
        Generate a realistic daily schedule from pending tasks with focus blocks and breaks.
        Incorporates stress-reduction logic: prioritizes Top 3 high/medium items first.
        """
        if not target_date or target_date.lower() == "today":
            target_date = date.today().isoformat()
        elif target_date.lower() == "tomorrow":
            target_date = (date.today().fromordinal(date.today().toordinal() + 1)).isoformat()

        tasks = task_manager.get_today_tasks()
        total_tasks_count = len(tasks)

        # Stress-reduction logic:
        # If there are many tasks, pick top high & medium tasks first (max 4-5 focus blocks)
        stress_notice = None
        if total_tasks_count > 5:
            stress_notice = (
                f"You have {total_tasks_count} pending tasks, but trying to do everything at once causes burnout. "
                f"I've selected the most impactful tasks for today so you can focus calmly."
            )
            # Prioritize High then Medium
            tasks = tasks[:5]

        # Starting time
        current_time = datetime.strptime(f"{target_date} {start_hour:02d}:00", "%Y-%m-%d %H:%M")
        
        # If scheduling for today and current time is already later in the day, adjust start
        now = datetime.now()
        if target_date == date.today().isoformat() and now.hour >= start_hour:
            # Round up to next half hour
            next_start_minute = 0 if now.minute < 30 else 30
            current_time = now.replace(minute=next_start_minute, second=0, microsecond=0)
            if now.minute >= 30:
                current_time += timedelta(minutes=30)
            else:
                current_time += timedelta(minutes=(30 - now.minute))

        schedule_blocks: List[Dict[str, Any]] = []

        if not tasks:
            # Default placeholder focus block if no tasks exist
            end_time = current_time + timedelta(hours=1)
            schedule_blocks.append({
                "start_time": current_time.strftime("%H:%M"),
                "end_time": end_time.strftime("%H:%M"),
                "title": "Creative / Deep Focus Block",
                "type": "focus",
                "priority": "Medium",
                "task_id": None
            })
        else:
            for i, task in enumerate(tasks):
                duration_mins = task.get("duration_minutes") or 60
                # Cap single focus block at 90 minutes for cognitive health
                block_duration = min(duration_mins, 90)
                end_time = current_time + timedelta(minutes=block_duration)

                schedule_blocks.append({
                    "start_time": current_time.strftime("%H:%M"),
                    "end_time": end_time.strftime("%H:%M"),
                    "title": task["title"],
                    "type": "focus",
                    "priority": task["priority"],
                    "task_id": task["id"]
                })
                current_time = end_time

                # Add a break after every focus block
                # Short 15 min break normally, or 45 min meal break if around 13:00 (1 PM)
                if current_time.hour == 13 and current_time.minute <= 30:
                    break_mins = 45
                    break_title = "Lunch & Refresh Break"
                else:
                    break_mins = 15
                    break_title = "Rest & Stretch Break"

                # Only add break if there are more tasks ahead
                if i < len(tasks) - 1:
                    break_end = current_time + timedelta(minutes=break_mins)
                    schedule_blocks.append({
                        "start_time": current_time.strftime("%H:%M"),
                        "end_time": break_end.strftime("%H:%M"),
                        "title": break_title,
                        "type": "break",
                        "priority": "Low",
                        "task_id": None
                    })
                    current_time = break_end

        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        now_str = datetime.now().isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO schedules (date, time_blocks, notes, created_at)
            VALUES (?, ?, ?, ?)
        """, (target_date, json.dumps(schedule_blocks), stress_notice or "", now_str))
        conn.commit()
        conn.close()

        return {
            "date": target_date,
            "blocks": schedule_blocks,
            "stress_notice": stress_notice,
            "total_tasks_considered": len(tasks),
            "total_pending_overall": total_tasks_count
        }

    @staticmethod
    def get_schedule(target_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Retrieve stored schedule for a date."""
        if not target_date or target_date.lower() == "today":
            target_date = date.today().isoformat()
        elif target_date.lower() == "tomorrow":
            target_date = (date.today().fromordinal(date.today().toordinal() + 1)).isoformat()

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM schedules WHERE date = ?", (target_date,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": row["id"],
            "date": row["date"],
            "blocks": json.loads(row["time_blocks"]),
            "notes": row["notes"],
            "created_at": row["created_at"]
        }

schedule_generator = ScheduleGenerator()
