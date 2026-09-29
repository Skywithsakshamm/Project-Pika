"""
End-to-End Simulation Test of the Section 27 First Working Demo Workflow.
"""
import asyncio
import sys
from pathlib import Path

# Fix Windows console UTF-8 output
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.assistant.selvie import selvie
from backend.tasks.manager import task_manager
from backend.reminders.engine import reminder_engine

async def run_demo():
    print("\n--- STEP 1: INITIAL STARTUP GREETING ---")
    greeting = await selvie.get_initial_greeting()
    print("Selvie says:", greeting["reply"])
    assert "Hey Saksham" in greeting["reply"]

    print("\n--- STEP 2: USER SPEAKS: 'Open YouTube and play study music' ---")
    res1 = await selvie.process_user_input("Open YouTube and play study music")
    print("Selvie response:", res1["reply"])
    print("Tools executed:", [t["tool"] for t in res1["tools_executed"]])
    assert any(t["tool"] == "play_media" for t in res1["tools_executed"])

    print("\n--- STEP 3: USER SPEAKS: 'Also add study probability for two hours and SIH documentation for one hour to today's plan' ---")
    res2 = await selvie.process_user_input("Also add study probability for two hours and SIH documentation for one hour to today's plan")
    print("Selvie response:", res2["reply"])
    print("Tools executed:", [t["tool"] for t in res2["tools_executed"]])
    assert any(t["tool"] == "create_task" for t in res2["tools_executed"])
    assert any(t["tool"] == "create_schedule" for t in res2["tools_executed"])

    today_tasks = task_manager.get_today_tasks()
    task_titles = [t["title"] for t in today_tasks]
    print("Active Tasks in DB:", task_titles)
    assert any("probability" in t.lower() for t in task_titles)
    assert any("sih" in t.lower() for t in task_titles)

    print("\n--- STEP 4: USER SPEAKS: 'Open WhatsApp' ---")
    res3 = await selvie.process_user_input("Open WhatsApp")
    print("Selvie response:", res3["reply"])
    print("Tools executed:", [t["tool"] for t in res3["tools_executed"]])
    assert any(t["tool"] == "open_application" for t in res3["tools_executed"])

    print("\n--- STEP 5: USER SPEAKS: 'Remind me at 7 PM to call my teammate' ---")
    res4 = await selvie.process_user_input("Remind me at 7 PM to call my teammate")
    print("Selvie response:", res4["reply"])
    print("Tools executed:", [t["tool"] for t in res4["tools_executed"]])
    assert any(t["tool"] == "create_reminder" for t in res4["tools_executed"])

    active_reminders = reminder_engine.get_active_reminders()
    print("Active Reminders in DB:", [r["message"] for r in active_reminders])
    assert any("teammate" in r["message"].lower() for r in active_reminders)

    print("\n[SUCCESS] All 5 steps of the Master Prompt Demo Workflow executed perfectly!\n")

if __name__ == "__main__":
    asyncio.run(run_demo())
