"""
LLM Client layer for Selvie.
Supports:
1. Local Ollama (llama3.1)
2. Fast-Path Offline Intent Parser (instant sub-20ms responses for core voice commands)
3. Configurable Cloud LLM (OpenAI/Gemini compatible format)
"""
import re
import json
import httpx
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from config.settings import settings
from backend.tools.registry import tool_registry
from backend.memory.memory_manager import memory_manager

SELVIE_SYSTEM_PROMPT = """You are Selvie, an intelligent, calm, friendly, and supportive AI personal companion for Windows desktop.
You are helping your user, Saksham.

Core Persona:
- Warm, natural, friendly, calm, conversational, lightly humorous when appropriate, stress-reducing.
- Understand and speak naturally in English and Hinglish.
- Keep answers concise and direct. Do NOT give long preachy motivational speeches.
- If Saksham feels stressed or overwhelmed, help simplify and break things down into small manageable steps.

Your Capabilities & Tools:
You have access to safe Windows tools:
- open_application(app_name): opens desktop apps (Spotify, WhatsApp, VS Code, Chrome, Notion, Discord, Explorer, Settings)
- open_website(url): opens websites in default browser
- search_web(query, engine): searches Google or YouTube
- play_media(query, platform): plays focus music / playlists on YouTube or Spotify, pauses/resumes
- create_task(title, priority, due_date, duration): adds to to-do list (priority: High, Medium, Low)
- complete_task(task_identifier): marks task complete
- delete_task(task_identifier): removes task
- get_today_tasks(): returns active tasks
- create_schedule(date): generates daily schedule with focus blocks and rest breaks
- get_schedule(date): gets daily schedule
- create_reminder(message, datetime): sets local reminder with Windows notification
- open_folder(path): opens File Explorer
- create_folder(path) / create_file(path, content)
- remember_fact(key, content) / recall_memories(query) / forget_memory(key)

Output Format:
You MUST respond with valid JSON adhering to this exact schema:
{
  "reply": "Your warm, natural spoken reply to Saksham here",
  "tools": [
    {
      "name": "tool_name",
      "arguments": { ... }
    }
  ]
}

If no tools are required (e.g. casual conversation or emotional support), leave "tools" as an empty list [].
"""

class FastIntentParser:
    """High-speed rule engine for instant execution of common voice commands."""

    @staticmethod
    def parse(user_input: str) -> Optional[Dict[str, Any]]:
        text = user_input.strip()
        lower = text.lower()

        # 1. Stress / Overwhelmed Hinglish triggers
        if any(p in lower for p in ["aaj bahut saare kaam hain", "samajh nahi aa raha kya karu", "bahut saara kaam hai"]):
            return {
                "reply": "Don't worry. Ek saath sab nahi karna. Tum mujhe saare tasks batao, main priority ke according plan bana deti hoon.",
                "tools": [{"name": "get_today_tasks", "arguments": {}}]
            }
        if any(p in lower for p in ["i'm stressed", "im stressed", "bahut saare kaam pending", "bahut kaam pending"]):
            return {
                "reply": "Relax. Pehle sab kuch ek saath solve nahi karte. Mujhe pending tasks batao, main unhe manageable steps mein divide kar deti hoon.",
                "tools": [{"name": "get_today_tasks", "arguments": {}}]
            }

        # 2. Greeting
        if lower in ["hey", "hello", "hi", "hey selvie", "hello selvie", "hi selvie"]:
            return {
                "reply": f"Hey Saksham! 👋 What can we do today?",
                "tools": []
            }

        # 3. Compound Voice Command: Open YouTube and play study music
        if ("open youtube" in lower or "play" in lower) and any(w in lower for w in ["study music", "focus music", "lofi", "playlist", "songs"]):
            clean_term = "study focus music"
            if "study music" in lower:
                clean_term = "study music"
            elif "focus music" in lower:
                clean_term = "focus music"
            elif "lofi" in lower:
                clean_term = "lofi hip hop study beats"
            return {
                "reply": f"Sure, opening YouTube and finding {clean_term}.",
                "tools": [
                    {"name": "play_media", "arguments": {"query": clean_term, "platform": "youtube"}}
                ]
            }

        # 4. Multi-task addition pattern:
        # "add study probability for two hours and SIH documentation for one hour to today's plan"
        if ("add" in lower or "put" in lower) and ("probability" in lower or "sih" in lower or "study" in lower) and ("plan" in lower or "to-do" in lower or "todo" in lower):
            tools = []
            if "probability" in lower:
                dur = 120 if ("two hour" in lower or "2 hour" in lower or "2hr" in lower) else 60
                tools.append({"name": "create_task", "arguments": {"title": "Study probability", "priority": "High", "due_date": "today", "duration": dur}})
            if "sih" in lower or "documentation" in lower:
                dur = 60 if ("one hour" in lower or "1 hour" in lower or "1hr" in lower) else 60
                tools.append({"name": "create_task", "arguments": {"title": "SIH documentation", "priority": "Medium", "due_date": "today", "duration": dur}})
            tools.append({"name": "create_schedule", "arguments": {"date": "today"}})
            return {
                "reply": "Done. I've added both tasks to today's plan. You have two focused blocks for them.",
                "tools": tools
            }

        # 5. Open App: Open WhatsApp / Spotify / VS Code / Chrome / Notion / Discord
        app_match = re.search(r'\b(?:open|launch|start)\s+(whatsapp|spotify|vs\s*code|vscode|chrome|notion|discord|settings|explorer|file\s+explorer|notepad)\b', lower)
        if app_match:
            app_name = app_match.group(1).title()
            if "Vs" in app_name:
                app_name = "VS Code"
            return {
                "reply": f"Opening {app_name}.",
                "tools": [{"name": "open_application", "arguments": {"app_name": app_name}}]
            }

        # 6. Open Website: Open YouTube / GitHub / ChatGPT / Gmail / Drive
        web_match = re.search(r'\b(?:open)\s+(youtube|github|chatgpt|chat\s*gpt|gmail|google\s*drive|drive)\b', lower)
        if web_match:
            site = web_match.group(1)
            urls = {
                "youtube": "https://www.youtube.com",
                "github": "https://github.com",
                "chatgpt": "https://chatgpt.com",
                "chat gpt": "https://chatgpt.com",
                "gmail": "https://mail.google.com",
                "google drive": "https://drive.google.com",
                "drive": "https://drive.google.com"
            }
            target_url = urls.get(site, f"https://www.{site}.com")
            return {
                "reply": f"Opening {site.title()}.",
                "tools": [{"name": "open_website", "arguments": {"url": target_url}}]
            }

        # 7. Reminders: "Remind me at 7 PM to call my teammate" / "Remind me in 30 minutes to ..."
        rem_match = re.search(r'remind\s+me\s+(?:at\s+(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)|in\s+(\d+\s*(?:minutes?|mins?|hours?|hrs?)))\s*(?:to\s+(.+)|that\s+(.+))?', lower)
        if rem_match:
            time_spec = rem_match.group(1) or rem_match.group(2)
            content = rem_match.group(3) or rem_match.group(4) or "check your pending task"
            return {
                "reply": f"Okay, I've set a reminder for {time_spec} to {content}.",
                "tools": [{"name": "create_reminder", "arguments": {"message": content.capitalize(), "datetime": time_spec}}]
            }

        # 8. Web Search: "Search Google for ..." or "Search YouTube for ..."
        search_match = re.search(r'search\s+(google|youtube)\s+for\s+(.+)', lower)
        if search_match:
            engine = search_match.group(1)
            q = search_match.group(2)
            return {
                "reply": f"Searching {engine.capitalize()} for '{q}'.",
                "tools": [{"name": "search_web", "arguments": {"query": q, "engine": engine}}]
            }

        # 9. Planning / What should I do today / Plan my day
        if any(p in lower for p in ["what should i do today", "plan my day", "make a schedule", "what's on my schedule", "whats my plan"]):
            return {
                "reply": "I'm checking your tasks and generating your focus blocks for today.",
                "tools": [
                    {"name": "get_today_tasks", "arguments": {}},
                    {"name": "create_schedule", "arguments": {"date": "today"}}
                ]
            }

        # 10. Single task creation: "Add finish my SIH documentation to my to-do list"
        add_task_match = re.search(r'add\s+(.+?)\s+(?:to\s+my\s+(?:to-do|todo|task)\s+list|to\s+today[\'s]*\s+plan)', lower)
        if add_task_match:
            task_title = add_task_match.group(1).capitalize()
            prio = "High" if any(w in lower for w in ["exam", "urgent", "important"]) else "Medium"
            return {
                "reply": f"Added '{task_title}' to your tasks.",
                "tools": [{"name": "create_task", "arguments": {"title": task_title, "priority": prio, "due_date": "today"}}]
            }

        # 11. Folder / File operations
        folder_match = re.search(r'open\s+my\s+([a-zA-Z0-9\s_-]+)\s+folder', lower)
        if folder_match:
            folder_name = folder_match.group(1)
            return {
                "reply": f"Opening your {folder_name} folder.",
                "tools": [{"name": "open_folder", "arguments": {"path": folder_name}}]
            }

        # 12. Media playback controls: pause, next song
        if lower in ["pause the music", "pause music", "pause song", "stop music", "pause"]:
            return {
                "reply": "Pausing media.",
                "tools": [{"name": "play_media", "arguments": {"query": "pause"}}]
            }
        if lower in ["play the next song", "next song", "skip song", "next track"]:
            return {
                "reply": "Skipping to next song.",
                "tools": [{"name": "play_media", "arguments": {"query": "next"}}]
            }

        return None


class LLMBrain:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.ollama_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    async def process_user_message(self, user_message: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        Process user voice or text input.
        1. Checks fast rule engine first for instant sub-20ms responsiveness.
        2. Falls back to Ollama llama3.1 local LLM.
        3. If Ollama is offline, falls back to intelligent natural response.
        """
        # Step 1: Fast Intent Parser
        fast_result = FastIntentParser.parse(user_message)
        if fast_result:
            return fast_result

        # Step 2: Query Ollama LLM
        if self.provider == "ollama" or self.provider == "auto":
            try:
                return await self._query_ollama(user_message, chat_history)
            except Exception as e:
                print(f"[LLM] Ollama query failed: {e}. Falling back to default assistant logic.")

        # Step 3: Cloud LLM fallback if configured
        if settings.CLOUD_API_KEY and settings.CLOUD_BASE_URL:
            try:
                return await self._query_cloud(user_message, chat_history)
            except Exception as e:
                print(f"[LLM] Cloud LLM query failed: {e}")

        # Step 4: Graceful intelligent fallback
        return self._fallback_response(user_message)

    async def _query_ollama(self, user_message: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        memory_context = memory_manager.get_context_summary()
        current_dt = datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")

        prompt = f"""System Context:
Current Date & Time: {current_dt}
User: Saksham
Stored Memories & Preferences:
{memory_context}

Available Tools:
{json.dumps(tool_registry.definitions, indent=2)}

User Request: {user_message}

Remember to respond ONLY with valid JSON containing "reply" and "tools".
"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": SELVIE_SYSTEM_PROMPT,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": 0.4,
                "top_p": 0.9
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{self.ollama_url}/api/generate", json=payload)
            if resp.status_code == 200:
                data = resp.json()
                response_text = data.get("response", "{}")
                try:
                    parsed = json.loads(response_text)
                    if "reply" in parsed:
                        if "tools" not in parsed or not isinstance(parsed["tools"], list):
                            parsed["tools"] = []
                        return parsed
                except json.JSONDecodeError:
                    return {"reply": response_text, "tools": []}

        raise RuntimeError(f"Ollama returned status {resp.status_code}")

    async def _query_cloud(self, user_message: str, chat_history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {settings.CLOUD_API_KEY}",
            "Content-Type": "application/json"
        }
        messages = [
            {"role": "system", "content": SELVIE_SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
        payload = {
            "model": settings.CLOUD_MODEL,
            "messages": messages,
            "response_format": {"type": "json_object"}
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{settings.CLOUD_BASE_URL.rstrip('/')}/chat/completions", headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                return json.loads(content)
        raise RuntimeError("Cloud LLM failed")

    def _fallback_response(self, user_message: str) -> Dict[str, Any]:
        """Conversational fallback when LLM is unavailable."""
        return {
            "reply": "I heard you, Saksham. Let's make sure everything runs smoothly today. What task should we tackle next?",
            "tools": []
        }

llm_brain = LLMBrain()
