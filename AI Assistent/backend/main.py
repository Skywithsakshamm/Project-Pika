"""
FastAPI Server & WebSocket Hub for Selvie Personal AI Assistant.
Hosts the backend REST API, static files, and real-time duplex WebSocket for the floating assistant.
"""
import os
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel

from config.settings import settings
from backend.database.db import init_db, get_db_connection
from backend.assistant.selvie import selvie
from backend.tasks.manager import task_manager
from backend.tasks.scheduler import schedule_generator
from backend.reminders.engine import reminder_engine
from backend.memory.memory_manager import memory_manager
from backend.automation.launcher import app_launcher
from backend.automation.startup import startup_manager
from backend.speech.tts import tts_engine
from backend.speech.stt import stt_engine

# Active WebSocket connections
active_connections: List[WebSocket] = []

def reminder_broadcast_callback(reminder: Dict[str, Any]):
    """Called by reminder engine when a reminder is triggered."""
    loop = asyncio.get_event_loop()
    msg = reminder.get("message", "Reminder")
    text_alert = f"Hey {settings.USER_NAME}, reminder: you wanted to {msg}."
    
    # Broadcast to all connected floating UI windows
    async def _send():
        audio_b64 = await tts_engine.synthesize_to_base64(text_alert)
        payload = json.dumps({
            "type": "reminder_triggered",
            "reminder": reminder,
            "announcement": text_alert,
            "audio_base64": audio_b64
        })
        for ws in list(active_connections):
            try:
                await ws.send_text(payload)
            except Exception:
                pass

    if loop.is_running():
        asyncio.create_task(_send())

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    init_db()
    reminder_engine.register_callback(reminder_broadcast_callback)
    reminder_engine.start()
    print("[Selvie Backend] Server started on", f"http://{settings.HOST}:{settings.PORT}")
    yield
    # Shutdown
    reminder_engine.stop()
    print("[Selvie Backend] Server stopped.")

app = FastAPI(title="Selvie AI Desktop Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Models -----------------
class ChatRequest(BaseModel):
    message: str

class TaskCreateRequest(BaseModel):
    title: str
    priority: str = "Medium"
    due_date: str = "today"
    due_time: str = ""
    duration_minutes: int = 60
    description: str = ""
    category: str = "General"

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[str] = None
    due_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    description: Optional[str] = None

class ReminderCreateRequest(BaseModel):
    message: str
    datetime: str
    is_recurring: bool = False
    repeat_pattern: str = ""

class MemoryCreateRequest(BaseModel):
    key: str
    content: str
    category: str = "preference"

class AppRegisterRequest(BaseModel):
    name: str
    command: str
    aliases: List[str] = []
    category: str = "Custom"

class ConfirmRequest(BaseModel):
    ticket_id: str
    approved: bool

class SettingsUpdateRequest(BaseModel):
    user_name: Optional[str] = None
    llm_provider: Optional[str] = None
    ollama_model: Optional[str] = None
    tts_voice: Optional[str] = None
    auto_start: Optional[bool] = None
    quiet_mode: Optional[bool] = None

# ----------------- Endpoints -----------------

@app.get("/api/greeting")
async def get_greeting():
    """Initial greeting when laptop starts or app opens."""
    return await selvie.get_initial_greeting()

@app.post("/api/chat")
async def chat(req: ChatRequest):
    """Process user text or transcribed voice query."""
    return await selvie.process_user_input(req.message)

@app.post("/api/confirm")
async def confirm_action(req: ConfirmRequest):
    """Approve or cancel a high-risk tool execution."""
    return await selvie.confirm_action(req.ticket_id, req.approved)

@app.post("/api/tts")
async def text_to_speech(req: ChatRequest):
    """Generate speech audio base64 for text."""
    audio_b64 = await tts_engine.synthesize_to_base64(req.message)
    return {"audio_base64": audio_b64}

@app.post("/api/voice-transcribe")
async def voice_transcribe(file: UploadFile = File(...)):
    """Transcribe uploaded audio file."""
    content = await file.read()
    res = stt_engine.transcribe_audio_bytes(content)
    return res

# Tasks
@app.get("/api/tasks")
async def list_tasks(status: Optional[str] = None, priority: Optional[str] = None):
    return task_manager.get_tasks(status, priority)

@app.get("/api/tasks/today")
async def list_today_tasks():
    return task_manager.get_today_tasks()

@app.get("/api/tasks/summary")
async def task_summary():
    return task_manager.get_summary()

@app.post("/api/tasks")
async def create_task(req: TaskCreateRequest):
    return task_manager.create_task(
        title=req.title,
        priority=req.priority,
        due_date=req.due_date,
        due_time=req.due_time,
        duration_minutes=req.duration_minutes,
        description=req.description,
        category=req.category
    )

@app.put("/api/tasks/{task_id}")
async def update_task(task_id: int, req: TaskUpdateRequest):
    return task_manager.update_task(task_id, req.dict(exclude_unset=True))

@app.post("/api/tasks/{task_id}/complete")
async def complete_task(task_id: int):
    return task_manager.complete_task(task_id)

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: int):
    return {"success": task_manager.delete_task(task_id)}

# Schedule
@app.get("/api/schedule")
async def get_schedule(date: Optional[str] = "today"):
    res = schedule_generator.get_schedule(date)
    if not res:
        # Auto generate if not created yet
        res = schedule_generator.generate_daily_schedule(date)
    return res

@app.post("/api/schedule/generate")
async def generate_schedule(date: Optional[str] = "today"):
    return schedule_generator.generate_daily_schedule(date)

# Reminders
@app.get("/api/reminders")
async def list_reminders():
    return reminder_engine.get_active_reminders()

@app.post("/api/reminders")
async def create_reminder(req: ReminderCreateRequest):
    return reminder_engine.create_reminder(req.message, req.datetime, req.is_recurring, req.repeat_pattern)

@app.delete("/api/reminders/{reminder_id}")
async def delete_reminder(reminder_id: int):
    return {"success": reminder_engine.delete_reminder(reminder_id)}

# Memories
@app.get("/api/memories")
async def list_memories(q: Optional[str] = None):
    return memory_manager.recall(q)

@app.post("/api/memories")
async def remember(req: MemoryCreateRequest):
    return memory_manager.remember(req.key, req.content, req.category)

@app.delete("/api/memories/{key}")
async def forget_memory(key: str):
    return {"success": memory_manager.forget(key)}

# Apps
@app.get("/api/apps")
async def list_apps():
    return app_launcher.list_registered_apps()

@app.post("/api/apps")
async def register_app(req: AppRegisterRequest):
    return app_launcher.register_custom_app(req.name, req.command, req.aliases, req.category)

@app.post("/api/apps/launch/{app_name}")
async def launch_app(app_name: str):
    return app_launcher.open_application(app_name)

# System & Settings
@app.get("/api/settings")
async def get_settings():
    return {
        "user_name": settings.USER_NAME,
        "assistant_name": settings.ASSISTANT_NAME,
        "llm_provider": settings.LLM_PROVIDER,
        "ollama_model": settings.OLLAMA_MODEL,
        "tts_voice": settings.TTS_VOICE,
        "global_hotkey": settings.GLOBAL_HOTKEY,
        "auto_start_windows": startup_manager.is_startup_enabled(),
        "quiet_mode": settings.QUIET_MODE,
        "confirmation_required": settings.CONFIRMATION_REQUIRED
    }

@app.post("/api/settings")
async def update_settings(req: SettingsUpdateRequest):
    if req.user_name is not None:
        settings.USER_NAME = req.user_name
        selvie.user_name = req.user_name
    if req.auto_start is not None:
        if req.auto_start:
            startup_manager.enable_startup()
        else:
            startup_manager.disable_startup()
    if req.quiet_mode is not None:
        settings.QUIET_MODE = req.quiet_mode
    if req.llm_provider is not None:
        settings.LLM_PROVIDER = req.llm_provider
    if req.ollama_model is not None:
        settings.OLLAMA_MODEL = req.ollama_model
    if req.tts_voice is not None:
        settings.TTS_VOICE = req.tts_voice
        tts_engine.default_voice = req.tts_voice
    return {"success": True}

# WebSocket for real-time bi-directional conversation
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            try:
                event = json.loads(raw_data)
                ev_type = event.get("type")

                if ev_type == "user_message":
                    user_text = event.get("text", "")
                    # Stream state: THINKING
                    await websocket.send_text(json.dumps({"type": "state_change", "state": "THINKING"}))
                    # Process
                    result = await selvie.process_user_input(user_text)
                    # Send response
                    await websocket.send_text(json.dumps({
                        "type": "assistant_response",
                        "reply": result["reply"],
                        "audio_base64": result["audio_base64"],
                        "tools_executed": result["tools_executed"],
                        "pending_confirmation": result.get("pending_confirmation")
                    }))

                elif ev_type == "confirm_action":
                    ticket_id = event.get("ticket_id")
                    approved = event.get("approved", False)
                    result = await selvie.confirm_action(ticket_id, approved)
                    await websocket.send_text(json.dumps({
                        "type": "assistant_response",
                        "reply": result["reply"],
                        "audio_base64": result["audio_base64"],
                        "result": result.get("result")
                    }))

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if websocket in active_connections:
            active_connections.remove(websocket)

# Static files for frontend and assets
assets_path = settings.ASSETS_DIR
if assets_path.exists():
    app.mount("/assets", StaticFiles(directory=str(assets_path)), name="assets")

frontend_dist = settings.FRONTEND_DIR / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    # Serve simple HTML fallback or development static
    frontend_public = settings.FRONTEND_DIR / "public"
    if frontend_public.exists():
        app.mount("/", StaticFiles(directory=str(frontend_public), html=True), name="public")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=False)
