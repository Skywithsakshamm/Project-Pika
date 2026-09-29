"""
Comprehensive Unit & Integration Test Suite for Selvie AI Assistant.
"""
import sys
import unittest
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.database.db import init_db, get_db_connection
from backend.tasks.manager import task_manager
from backend.tasks.scheduler import schedule_generator
from backend.reminders.engine import reminder_engine
from backend.memory.memory_manager import memory_manager
from backend.automation.launcher import app_launcher
from backend.tools.registry import tool_registry
from backend.llm.client import FastIntentParser

class TestSelvie(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_task_lifecycle(self):
        """Test task creation, completion, and retrieval."""
        task = task_manager.create_task(
            title="Study probability for two hours",
            priority="High",
            duration_minutes=120,
            category="Academics"
        )
        self.assertIsNotNone(task)
        self.assertEqual(task["title"], "Study probability for two hours")
        self.assertEqual(task["priority"], "High")
        self.assertEqual(task["status"], "Pending")

        # Complete task
        completed = task_manager.complete_task(task["id"])
        self.assertIsNotNone(completed)
        self.assertEqual(completed["status"], "Completed")

        # Cleanup
        deleted = task_manager.delete_task(task["id"])
        self.assertTrue(deleted)

    def test_02_schedule_generator(self):
        """Test schedule generation with focus blocks and breaks."""
        # Create 2 sample tasks
        t1 = task_manager.create_task("SIH Documentation", "Medium", duration_minutes=60)
        t2 = task_manager.create_task("Algorithm Practice", "High", duration_minutes=90)

        schedule = schedule_generator.generate_daily_schedule(target_date="today", start_hour=10)
        self.assertIn("blocks", schedule)
        self.assertTrue(len(schedule["blocks"]) >= 2)

        # Verify focus block exists
        types = [b["type"] for b in schedule["blocks"]]
        self.assertIn("focus", types)

        # Cleanup
        task_manager.delete_task(t1["id"])
        task_manager.delete_task(t2["id"])

    def test_03_stress_reduction_logic(self):
        """Verify Selvie detects overload when > 5 tasks exist."""
        created_ids = []
        for i in range(7):
            t = task_manager.create_task(f"Task Overload {i}", "Medium")
            created_ids.append(t["id"])

        summary = task_manager.get_summary()
        self.assertTrue(summary["is_overwhelmed"])

        schedule = schedule_generator.generate_daily_schedule("today")
        self.assertIsNotNone(schedule.get("stress_notice"))

        for tid in created_ids:
            task_manager.delete_task(tid)

    def test_04_reminder_parsing(self):
        """Test reminder relative & explicit time parsing."""
        rem = reminder_engine.create_reminder("Call teammate", "7 PM")
        self.assertIsNotNone(rem)
        self.assertEqual(rem["message"], "Call teammate")
        self.assertTrue("19:00" in rem["trigger_time"] or "07:00" in rem["trigger_time"])

        reminder_engine.delete_reminder(rem["id"])

    def test_05_memory_sanitization(self):
        """Ensure passwords and API keys are strictly rejected by memory store."""
        res_safe = memory_manager.remember("favorite_framework", "React and FastAPI")
        self.assertTrue(res_safe["success"])

        res_unsafe = memory_manager.remember("api_key", "sk-123456789secretkey")
        self.assertFalse(res_unsafe["success"])
        self.assertIn("safety", res_unsafe["message"])

        memory_manager.forget("favorite_framework")

    def test_06_fast_intent_parser(self):
        """Test sub-20ms rule responses for natural voice commands."""
        # 1. YouTube & Study music compound command
        res1 = FastIntentParser.parse("Open YouTube and play study music")
        self.assertIsNotNone(res1)
        self.assertIn("study music", res1["reply"].lower())
        self.assertEqual(res1["tools"][0]["name"], "play_media")

        # 2. WhatsApp application command
        res2 = FastIntentParser.parse("Open WhatsApp")
        self.assertIsNotNone(res2)
        self.assertEqual(res2["tools"][0]["name"], "open_application")
        self.assertEqual(res2["tools"][0]["arguments"]["app_name"], "Whatsapp")

        # 3. Reminder command
        res3 = FastIntentParser.parse("Remind me at 7 PM to call my teammate")
        self.assertIsNotNone(res3)
        self.assertEqual(res3["tools"][0]["name"], "create_reminder")

        # 4. Hinglish stress expression
        res4 = FastIntentParser.parse("Selvie, aaj bahut saare kaam hain aur mujhe samajh nahi aa raha kya karu.")
        self.assertIsNotNone(res4)
        self.assertIn("Don't worry", res4["reply"])

    def test_07_safety_confirmation_policy(self):
        """Ensure destructive actions trigger a confirmation ticket."""
        # delete_file is high risk
        exec_res = tool_registry.execute_tool("delete_file", {"path": "important_file.txt"})
        self.assertEqual(exec_res.get("status"), "requires_confirmation")
        self.assertIn("ticket_id", exec_res)

        # Confirm cancellation
        ticket_id = exec_res["ticket_id"]
        cancel_res = tool_registry.confirm_action(ticket_id, approved=False)
        self.assertTrue(cancel_res.get("cancelled"))

if __name__ == "__main__":
    unittest.main()
