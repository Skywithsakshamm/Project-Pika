"""
Structured Tool System and Safety Confirmation Policy for Selvie.
Routes actions, validates inputs, and intercepts high-risk operations for user confirmation.
"""
import uuid
import os
import subprocess
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Callable
from config.settings import settings
from backend.tasks.manager import task_manager
from backend.tasks.scheduler import schedule_generator
from backend.reminders.engine import reminder_engine
from backend.memory.memory_manager import memory_manager
from backend.automation.launcher import app_launcher

# Pending actions awaiting user confirmation
_PENDING_CONFIRMATIONS: Dict[str, Dict[str, Any]] = {}

class ToolRegistry:
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.definitions: List[Dict[str, Any]] = []
        self._register_default_tools()

    def register(self, name: str, description: str, parameters: Dict[str, Any], is_high_risk: bool = False):
        """Decorator to register a tool function."""
        def decorator(func: Callable):
            self.tools[name] = func
            self.definitions.append({
                "name": name,
                "description": description,
                "parameters": parameters,
                "is_high_risk": is_high_risk
            })
            return func
        return decorator

    def _register_default_tools(self):
        # 1. Open Application
        self.register(
            name="open_application",
            description="Launch a desktop application or registered software like Spotify, WhatsApp, VS Code, Chrome, etc.",
            parameters={
                "type": "object",
                "properties": {
                    "app_name": {"type": "string", "description": "Name of the application to open, e.g. 'Spotify', 'WhatsApp', 'VS Code'"}
                },
                "required": ["app_name"]
            },
            is_high_risk=False
        )(lambda app_name: app_launcher.open_application(app_name))

        # 2. Open Website
        self.register(
            name="open_website",
            description="Open a website URL in the user's default browser.",
            parameters={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Website URL or domain, e.g. 'github.com', 'chatgpt.com', 'mail.google.com'"}
                },
                "required": ["url"]
            },
            is_high_risk=False
        )(lambda url: app_launcher.open_website(url))

        # 3. Search Web
        self.register(
            name="search_web",
            description="Perform a search on Google or YouTube.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query to look up"},
                    "engine": {"type": "string", "enum": ["google", "youtube"], "default": "google"}
                },
                "required": ["query"]
            },
            is_high_risk=False
        )(lambda query, engine="google": app_launcher.search_web(query, engine))

        # 4. Play Media
        self.register(
            name="play_media",
            description="Play music, playlists, or control media playback (pause, next, previous).",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Song name, artist, playlist like 'study music', or control commands 'pause', 'next'"},
                    "platform": {"type": "string", "enum": ["auto", "youtube", "spotify"], "default": "auto"}
                }
            },
            is_high_risk=False
        )(lambda query="focus music", platform="auto": app_launcher.play_media(query, platform))

        # 5. Create Task
        self.register(
            name="create_task",
            description="Add a new task to the user's smart to-do list.",
            parameters={
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Title of the task"},
                    "priority": {"type": "string", "enum": ["High", "Medium", "Low"], "default": "Medium"},
                    "due_date": {"type": "string", "description": "Date due, e.g. 'today', 'tomorrow', '2026-09-30'"},
                    "due_time": {"type": "string", "description": "Time due, e.g. '19:00', '7 PM'"},
                    "duration": {"type": "integer", "description": "Estimated duration in minutes (e.g. 60, 120)", "default": 60}
                },
                "required": ["title"]
            },
            is_high_risk=False
        )(lambda title, priority="Medium", due_date="today", due_time="", duration=60:
            task_manager.create_task(title=title, priority=priority, due_date=due_date, due_time=due_time, duration_minutes=duration))

        # 6. Complete Task
        self.register(
            name="complete_task",
            description="Mark a task as completed by title or ID.",
            parameters={
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "Task ID number or matching title substring"}
                },
                "required": ["task_identifier"]
            },
            is_high_risk=False
        )(lambda task_identifier: task_manager.complete_task(task_identifier))

        # 7. Delete Task
        self.register(
            name="delete_task",
            description="Remove a task from the to-do list.",
            parameters={
                "type": "object",
                "properties": {
                    "task_identifier": {"type": "string", "description": "Task ID or matching title substring"}
                },
                "required": ["task_identifier"]
            },
            is_high_risk=False
        )(lambda task_identifier: {"success": task_manager.delete_task(task_identifier)})

        # 8. Get Today Tasks
        self.register(
            name="get_today_tasks",
            description="Get the list of active tasks for today.",
            parameters={"type": "object", "properties": {}},
            is_high_risk=False
        )(lambda: task_manager.get_today_tasks())

        # 9. Create Schedule
        self.register(
            name="create_schedule",
            description="Generate a realistic daily schedule with focus blocks and breaks.",
            parameters={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Target date, 'today' or 'tomorrow'", "default": "today"}
                }
            },
            is_high_risk=False
        )(lambda date="today": schedule_generator.generate_daily_schedule(date))

        # 10. Get Schedule
        self.register(
            name="get_schedule",
            description="Get the existing daily schedule for a date.",
            parameters={
                "type": "object",
                "properties": {
                    "date": {"type": "string", "default": "today"}
                }
            },
            is_high_risk=False
        )(lambda date="today": schedule_generator.get_schedule(date))

        # 11. Create Reminder
        self.register(
            name="create_reminder",
            description="Set a local reminder with a Windows notification and voice prompt.",
            parameters={
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "What to remind the user about"},
                    "datetime": {"type": "string", "description": "When to remind, e.g. '7 PM', 'in 30 minutes', 'tomorrow 9 AM'"}
                },
                "required": ["message", "datetime"]
            },
            is_high_risk=False
        )(lambda message, datetime: reminder_engine.create_reminder(message, datetime))

        # 12. Open Folder
        self.register(
            name="open_folder",
            description="Open a folder in Windows File Explorer (e.g. 'projects', 'downloads').",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path or known folder name"}
                },
                "required": ["path"]
            },
            is_high_risk=False
        )(lambda path: app_launcher.open_folder(path))

        # 13. Create Folder
        self.register(
            name="create_folder",
            description="Create a new folder.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Folder name or path"}
                },
                "required": ["path"]
            },
            is_high_risk=False
        )(lambda path: app_launcher.create_folder(path))

        # 14. Create File
        self.register(
            name="create_file",
            description="Create a new text or notes file.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File name or path"},
                    "content": {"type": "string", "default": ""}
                },
                "required": ["path"]
            },
            is_high_risk=False
        )(lambda path, content="": app_launcher.create_file(path, content))

        # 15. Delete File (HIGH RISK - Requires Confirmation)
        self.register(
            name="delete_file",
            description="Permanently delete a file from disk. HIGH RISK.",
            parameters={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path of the file to delete"}
                },
                "required": ["path"]
            },
            is_high_risk=True
        )(lambda path: self._execute_delete_file(path))

        # 16. Store Memory
        self.register(
            name="remember_fact",
            description="Remember a non-sensitive fact, preference, or habit about the user.",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Short memory key or topic"},
                    "content": {"type": "string", "description": "The information to remember"}
                },
                "required": ["key", "content"]
            },
            is_high_risk=False
        )(lambda key, content: memory_manager.remember(key, content))

        # 17. Recall Memory
        self.register(
            name="recall_memories",
            description="Recall stored memories or preferences.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Topic or keyword, or empty for all"}
                }
            },
            is_high_risk=False
        )(lambda query="": memory_manager.recall(query if query else None))

        # 18. Forget Memory
        self.register(
            name="forget_memory",
            description="Delete specific memory or clear memories.",
            parameters={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Memory key or topic to forget"}
                },
                "required": ["key"]
            },
            is_high_risk=False
        )(lambda key: {"deleted": memory_manager.forget(key)})

        # 19. Get Current Time & Date
        self.register(
            name="get_current_time",
            description="Get the current local time, day of the week, and date.",
            parameters={"type": "object", "properties": {}},
            is_high_risk=False
        )(lambda: {
            "time": datetime.now().strftime("%I:%M %p"),
            "date": datetime.now().strftime("%A, %B %d, %Y"),
            "iso": datetime.now().isoformat()
        })

    def _execute_delete_file(self, path: str) -> Dict[str, Any]:
        target = os.path.expanduser(path)
        if not os.path.exists(target):
            return {"success": False, "message": f"File '{path}' does not exist."}
        try:
            os.remove(target)
            return {"success": True, "message": f"Permanently deleted '{path}'."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute_tool(self, name: str, arguments: Dict[str, Any], confirmed: bool = False) -> Dict[str, Any]:
        """Execute a tool with risk evaluation and confirmation intercept."""
        if name not in self.tools:
            return {"success": False, "error": f"Tool '{name}' is not recognized."}

        # Check if high risk and not yet confirmed
        tool_meta = next((t for t in self.definitions if t["name"] == name), None)
        if tool_meta and tool_meta["is_high_risk"] and settings.CONFIRMATION_REQUIRED and not confirmed:
            ticket_id = str(uuid.uuid4())[:8]
            _PENDING_CONFIRMATIONS[ticket_id] = {
                "ticket_id": ticket_id,
                "tool_name": name,
                "arguments": arguments,
                "created_at": datetime.now().isoformat(),
                "prompt": f"This action ({name} with {arguments}) will modify or delete data. Should I proceed?"
            }
            return {
                "status": "requires_confirmation",
                "ticket_id": ticket_id,
                "tool_name": name,
                "arguments": arguments,
                "confirmation_prompt": _PENDING_CONFIRMATIONS[ticket_id]["prompt"]
            }

        # Safe execution
        func = self.tools[name]
        try:
            result = func(**arguments)
            return {"status": "completed", "result": result}
        except Exception as e:
            print(f"[ToolRegistry] Error executing '{name}': {e}")
            return {"status": "error", "error": str(e)}

    def confirm_action(self, ticket_id: str, approved: bool) -> Dict[str, Any]:
        """Process user confirmation response for a pending action."""
        if ticket_id not in _PENDING_CONFIRMATIONS:
            return {"success": False, "message": "Confirmation ticket not found or expired."}

        ticket = _PENDING_CONFIRMATIONS.pop(ticket_id)
        if not approved:
            return {"success": False, "cancelled": True, "message": f"Action '{ticket['tool_name']}' was cancelled."}

        return self.execute_tool(ticket["tool_name"], ticket["arguments"], confirmed=True)

tool_registry = ToolRegistry()
