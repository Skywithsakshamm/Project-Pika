# Selvie — Personal AI Desktop Assistant 🌸
> **ONE VOICE → ONE ASSISTANT → MANY ACTIONS**  
> *Always with you, right from the moment you open your laptop.*

Selvie is a voice-first Windows personal desktop AI companion designed specifically for **Saksham**. Built with a warm, natural Indian female voice, intelligent task and schedule management, local Ollama LLM brain, Windows automation, and a minimalist floating glassmorphic overlay.

![Selvie Avatar](assets/selvie_avatar.jpg)

---

## 🌟 Key Features

1. **Voice-First Experience (No Dashboard Required)**:
   - Starts automatically in the background when Windows boots.
   - Initial greeting: *"Hey Saksham! 👋 What can we do today?"*
   - Floating assistant widget with animated orb, live waveform visualizer, and microphone button.
   - Global Hotkey: `Ctrl + Space` toggles voice listening anywhere in Windows.

2. **Natural Indian Female Voice**:
   - High-fidelity **Edge TTS** Indian English voice (`en-IN-NeerjaExpressiveNeural` / `en-IN-NeerjaNeural`).
   - Seamless understanding and natural replies in English and **Hinglish**.
   - Offline fallback to Windows SAPI5 / pyttsx3.

3. **Intelligent AI Brain (Ollama + Fast Intent Router)**:
   - Powered by local **Ollama** (`llama3.1`).
   - Sub-20ms ultra-fast offline intent parser for common system, media, and task actions.
   - Safe tool-execution architecture: LLM never runs raw shell commands directly.

4. **Stress-Reduction Daily Schedule Generator**:
   - Detects workload overload (>5 tasks) and extracts top high-priority tasks to prevent burnout.
   - Creates realistic schedules with dedicated focus blocks, 15-minute rest breaks, and lunch buffers.

5. **Smart To-Do List**:
   - High, Medium, and Low priorities with estimated durations.
   - Fuzzy search and voice completion (e.g. *"Mark my SIH work as complete"*).

6. **Active Reminders Engine**:
   - Local background thread checking every 3 seconds.
   - Fires native Windows Toast Notifications + Spoken voice announcement (*"Hey Saksham, reminder: you wanted to call your teammate"*).

7. **Safe Windows App & Web Launcher**:
   - Opens apps: YouTube, Spotify, WhatsApp, Chrome, VS Code, Notion, Discord, File Explorer, Windows Settings.
   - Custom app registration support.
   - Destructive actions (e.g. deleting files) trigger an interactive **Safety Confirmation Guard**.

8. **Local Memory & Privacy**:
   - Remembers habits, workflows, and preferences locally in SQLite.
   - Strictly blocks passwords, API keys, and sensitive tokens.

---

## 📁 Project Structure

```text
AI Assistent/
│
├── assets/
│   └── selvie_avatar.jpg          # High-resolution Selvie avatar
│
├── backend/
│   ├── assistant/
│   │   └── selvie.py             # Core assistant pipeline & greetings
│   ├── automation/
│   │   ├── launcher.py           # Windows apps, websites, media & folder launcher
│   │   ├── hotkey.py             # Win32 RegisterHotKey (Ctrl+Space) listener
│   │   └── startup.py            # Windows Startup Registry manager
│   ├── database/
│   │   ├── db.py                 # SQLite tables, schemas & migrations
│   │   └── selvie.db             # Local database
│   ├── llm/
│   │   └── client.py             # Ollama (llama3.1) & Fast Intent Parser
│   ├── memory/
│   │   └── memory_manager.py     # Local context memory store & sanitizer
│   ├── reminders/
│   │   └── engine.py             # Background timer & Windows toast engine
│   ├── speech/
│   │   ├── tts.py                # Edge-TTS Indian female voice & cache
│   │   └── stt.py                # Speech-to-Text audio transcriber
│   ├── tasks/
│   │   ├── manager.py            # Smart To-Do list CRUD & priorities
│   │   └── scheduler.py          # Daily schedule & stress-reduction generator
│   ├── tools/
│   │   └── registry.py           # Validated tool definitions & safety policy
│   ├── desktop_app.py            # PySide6 frameless floating desktop overlay
│   └── main.py                   # FastAPI REST API & WebSocket server
│
├── config/
│   └── settings.py               # Pydantic configuration & environment loader
│
├── frontend/
│   └── public/
│       ├── index.html            # Floating assistant glassmorphic UI
│       ├── app.css               # Obsidian & neon purple/cyan styling
│       ├── app.js                # Web Audio API, Web Speech STT & IPC
│       └── selvie_avatar.jpg     # Avatar asset
│
├── scripts/
│   └── setup_windows.ps1         # Windows setup & auto-start PowerShell script
│
├── tests/
│   ├── test_selvie.py            # Unit test suite (Tasks, Scheduler, Tools)
│   └── test_demo_flow.py         # End-to-end simulation of Section 27 demo
│
├── run_selvie.bat                # 1-Click Windows Batch Launcher
├── run_selvie.py                 # Python launcher entry point
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment configuration template
└── README.md                     # Comprehensive documentation
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Windows 10 / 11**
- **Python 3.10+** (Python 3.14+ supported)
- **Ollama** with `llama3.1` (Optional but recommended for open-ended conversation)

### 2. Installation
Open PowerShell in the project directory:
```powershell
python -m pip install -r requirements.txt
```

### 3. Launching Selvie
Simply double-click:
```bat
run_selvie.bat
```
Or run from PowerShell/Terminal:
```powershell
python run_selvie.py
```

To run only the backend server (accessible in any web browser at `http://127.0.0.1:8765`):
```powershell
python run_selvie.py --backend-only
```

---

## 🎙️ Voice Interaction & Commands

Click the glowing microphone button or press **`Ctrl + Space`** anywhere in Windows and speak naturally:

### Applications & Media
- *"Open YouTube and play study music."*
- *"Open Spotify."*
- *"Open WhatsApp."*
- *"Open VS Code."*
- *"Pause the music."*
- *"Play the next song."*

### Tasks & Daily Planning
- *"Add study probability for two hours and SIH documentation for one hour to today's plan."*
- *"What should I do today?"*
- *"Plan my day."*
- *"Mark my SIH work as complete."*

### Reminders
- *"Remind me at 7 PM to call my teammate."*
- *"Remind me in 30 minutes to drink water."*

### Hinglish & Emotional Support
- *"Selvie, aaj bahut saare kaam hain aur mujhe samajh nahi aa raha kya karu."*
  > *Selvie: "Don't worry. Ek saath sab nahi karna. Tum mujhe saare tasks batao, main priority ke according plan bana deti hoon."*
- *"Selvie, I'm stressed. Bahut saare kaam pending hain."*
  > *Selvie: "Relax. Pehle sab kuch ek saath solve nahi karte. Mujhe pending tasks batao, main unhe manageable steps mein divide kar deti hoon."*

---

## ⚙️ Configuration & Windows Auto-Start

### Enabling Windows Auto-Start
To launch Selvie automatically whenever your laptop turns on:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1 -EnableAutoStart
```
Or toggle **"Start Selvie with Windows"** in the Assistant Settings panel inside the app!

### Changing Voice / LLM in `.env`
Create `.env` from `.env.example`:
```ini
USER_NAME=Saksham
TTS_VOICE=en-IN-NeerjaExpressiveNeural
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.1
GLOBAL_HOTKEY=Ctrl+Space
CONFIRMATION_REQUIRED=true
```

---

## 🧪 Running the Tests

To run the complete unit test suite:
```powershell
python -m unittest tests/test_selvie.py
```

To run the Section 27 Demo Workflow validation:
```powershell
python tests/test_demo_flow.py
```

---

## 🛡️ Safety & Privacy Policy
- **No Cloud Secret Leaks**: All credentials stay local.
- **Memory Sanitizer**: Memory manager automatically rejects passwords, tokens, API keys, and PINs.
- **Destructive Action Intercept**: Deleting files or system changes triggers a confirmation modal asking for explicit approval before execution.

---

### ✨ Built with Love for Saksham
Selvie brings effortless voice-first productivity and calm companionship right to your desktop.
