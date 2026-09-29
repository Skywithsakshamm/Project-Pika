"""
Selvie Core Assistant Engine.
Coordinates voice input, LLM reasoning, tool routing, confirmation guards, and speech synthesis.
"""
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from config.settings import settings
from backend.database.db import get_db_connection
from backend.tasks.manager import task_manager
from backend.tasks.scheduler import schedule_generator
from backend.tools.registry import tool_registry
from backend.llm.client import llm_brain
from backend.speech.tts import tts_engine

class SelvieAssistant:
    def __init__(self):
        self.user_name = settings.USER_NAME

    async def get_initial_greeting(self) -> Dict[str, Any]:
        """
        Generate the warm startup greeting (Section 1 & 14).
        'Hey Saksham! 👋 What can we do today?'
        If today's schedule already exists:
        'You have three important things planned today. Want me to walk you through them?'
        """
        today_tasks = task_manager.get_today_tasks()
        task_count = len(today_tasks)

        if task_count >= 2:
            reply = f"Hey {self.user_name}! 👋 You have {task_count} things planned for today. Want me to walk you through them?"
        elif task_count == 1:
            reply = f"Hey {self.user_name}! 👋 You have 1 task on your agenda today: '{today_tasks[0]['title']}'. Ready to start?"
        else:
            reply = f"Hey {self.user_name}! 👋 What can we do today?"

        audio_base64 = await tts_engine.synthesize_to_base64(reply)
        return {
            "reply": reply,
            "audio_base64": audio_base64,
            "tasks_count": task_count
        }

    async def process_user_input(self, user_text: str) -> Dict[str, Any]:
        """
        Execute full assistant pipeline:
        User Text -> LLM Reasoning / Intent -> Tool Execution -> TTS Audio -> Return
        """
        clean_text = user_text.strip()
        if not clean_text:
            return {"reply": "", "audio_base64": "", "tools_executed": []}

        # Save user message to history
        self._save_conversation("user", clean_text)

        # 1. LLM Brain Reasoning
        brain_output = await llm_brain.process_user_message(clean_text)
        reply = brain_output.get("reply", "Understood.")
        tools_to_run = brain_output.get("tools", [])

        # 2. Tool Execution
        tools_executed = []
        pending_confirmation = None

        for t in tools_to_run:
            name = t.get("name")
            args = t.get("arguments", {})
            exec_res = tool_registry.execute_tool(name, args)

            if exec_res.get("status") == "requires_confirmation":
                pending_confirmation = exec_res
                reply = exec_res.get("confirmation_prompt", "This action requires confirmation. Should I proceed?")
                tools_executed.append({"tool": name, "status": "pending_confirmation", "ticket_id": exec_res.get("ticket_id")})
                break
            else:
                tools_executed.append({"tool": name, "status": "completed", "result": exec_res.get("result")})

        # Save assistant reply to history
        self._save_conversation("assistant", reply)

        # 3. Text-to-Speech synthesis
        audio_base64 = await tts_engine.synthesize_to_base64(reply)

        return {
            "reply": reply,
            "audio_base64": audio_base64,
            "tools_executed": tools_executed,
            "pending_confirmation": pending_confirmation
        }

    async def confirm_action(self, ticket_id: str, approved: bool) -> Dict[str, Any]:
        """Process user confirmation for a high-risk action."""
        result = tool_registry.confirm_action(ticket_id, approved)
        if approved:
            reply = "Action confirmed and executed."
        else:
            reply = "Action cancelled. Nothing was changed."

        audio_base64 = await tts_engine.synthesize_to_base64(reply)
        return {
            "reply": reply,
            "audio_base64": audio_base64,
            "result": result
        }

    def _save_conversation(self, role: str, content: str):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO conversations (role, content, timestamp) VALUES (?, ?, ?)",
                (role, content, datetime.now().isoformat())
            )
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Selvie] Error saving conversation: {e}")

selvie = SelvieAssistant()
